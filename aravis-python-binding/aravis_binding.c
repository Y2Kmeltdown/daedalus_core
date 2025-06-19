#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <aravis-0.8/arv.h>
#include <stdlib.h>
#include <stdio.h>

static guint64 frame_count    = 0;

// Module-level variables
static PyObject* AravisError;

// Generator state struct
typedef struct {
    PyObject_HEAD
    ArvCamera *camera;
    ArvStream *stream;
    int remaining; // -1 means infinite
    int width;
    int height;
    int npix;
    int bytes_per_pixel;
    int started;
} BufferStreamGen;

static void BufferStreamGen_dealloc(BufferStreamGen *self) {
    if (self->started && self->camera) {
        arv_camera_stop_acquisition(self->camera, NULL);
        self->started = 0;
    }
    if (self->stream) {
        g_clear_object(&self->stream);
        self->stream = NULL;
    }
    if (self->camera) {
        g_clear_object(&self->camera);
        self->camera = NULL;
    }
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *BufferStreamGen_iter(PyObject *self) {
    Py_INCREF(self);
    return self;
}

static PyObject *BufferStreamGen_iternext(PyObject *self) {
    BufferStreamGen *gen = (BufferStreamGen *)self;
    if (gen->remaining == 0) {
        // End of iteration (finite mode)
        return NULL;
    }
    ArvBuffer *buffer = arv_stream_pop_buffer(gen->stream);
    if (!ARV_IS_BUFFER(buffer)) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to get buffer");
        return NULL;
    }
    size_t buffer_sz;
    const void *raw = arv_buffer_get_data(buffer, &buffer_sz);
    PyObject *py_bytes = NULL;
    if (raw) {
        guint8 *stretched = malloc(gen->npix);
        if (!stretched) {
            arv_stream_push_buffer(gen->stream, buffer);
            PyErr_SetString(PyExc_MemoryError, "Out of memory");
            return NULL;
        }
        if (gen->bytes_per_pixel == 1) {
            const guint8 *p = raw;
            guint8 minv = UCHAR_MAX, maxv = 0;
            for (int i = 0; i < gen->npix; i++) {
                if (p[i] < minv) minv = p[i];
                if (p[i] > maxv) maxv = p[i];
            }
            if (maxv > minv) {
                float scale = 255.0f / (maxv - minv);
                for (int i = 0; i < gen->npix; i++)
                    stretched[i] = (guint8)((p[i] - minv) * scale + 0.5f);
            } else {
                memset(stretched, 0, gen->npix);
            }
        } else if (gen->bytes_per_pixel == 2) {
            const guint16 *p = raw;
            guint16 minv = USHRT_MAX, maxv = 0;
            for (int i = 0; i < gen->npix; i++) {
                if (p[i] < minv) minv = p[i];
                if (p[i] > maxv) maxv = p[i];
            }
            if (maxv > minv) {
                float scale = 255.0f / (maxv - minv);
                for (int i = 0; i < gen->npix; i++)
                    stretched[i] = (guint8)((p[i] - minv) * scale + 0.5f);
            } else {
                memset(stretched, 0, gen->npix);
            }
        } else {
            memset(stretched, 0, gen->npix);
        }
        py_bytes = PyBytes_FromStringAndSize((const char *)stretched, gen->npix);
        free(stretched);
    } else {
        py_bytes = PyBytes_FromStringAndSize("", 0);
    }
    arv_stream_push_buffer(gen->stream, buffer);
    if (gen->remaining > 0)
        gen->remaining--;
    return py_bytes;
}

static PyTypeObject BufferStreamGenType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "aravis.BufferStreamGen",
    .tp_basicsize = sizeof(BufferStreamGen),
    .tp_dealloc = (destructor)BufferStreamGen_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_iter = BufferStreamGen_iter,
    .tp_iternext = BufferStreamGen_iternext,
};

// Helper function to convert GError to Python exception
static void handle_gerror(GError *error) {
    if (error) {
        PyErr_SetString(AravisError, error->message);
        g_error_free(error);
    }
}

static PyObject* get_camera_buffer(PyObject* self, PyObject* args) {
    ArvCamera *camera;
    ArvBuffer *buffer;
    GError *error = NULL;
    const void *data;
    size_t buffer_sz;
    PyObject *result;

    /* Connect to the first available camera */
    camera = arv_camera_new(NULL, &error);

    if (ARV_IS_CAMERA(camera)) {
        printf("Found camera '%s'\n", arv_camera_get_model_name(camera, NULL));

        /* Acquire a single buffer */
        buffer = arv_camera_acquisition(camera, 0, &error);

        if (ARV_IS_BUFFER(buffer)) {
            /* Get buffer data */
            const void *raw = arv_buffer_get_data(buffer, &buffer_sz);
            if (raw) {
                /* 2) Dimensions */
                guint width  = arv_buffer_get_image_width(buffer);
                guint height = arv_buffer_get_image_height(buffer);
                guint npix   = width * height;

                /* 3) Pixel format */
                guint pf    = arv_buffer_get_image_pixel_format(buffer);
                guint bpp   = ARV_PIXEL_FORMAT_BIT_PER_PIXEL(pf);
                guint bytes = bpp / 8;

                /* 4) Contrast-stretch */
                guint8 *stretched = malloc(npix);
                if (!stretched) {
                    g_printerr("Out of memory saving frame %lu\n",
                            (unsigned long)frame_count);
                } else {
                    if (bytes == 1) {
                        const guint8 *p = raw;
                        guint8 minv = UCHAR_MAX, maxv = 0;
                        for (guint i = 0; i < npix; i++) {
                            if (p[i] < minv) minv = p[i];
                            if (p[i] > maxv) maxv = p[i];
                        }
                        if (maxv > minv) {
                            float scale = 255.0f / (maxv - minv);
                            for (guint i = 0; i < npix; i++)
                                stretched[i] = (guint8)((p[i] - minv) * scale + 0.5f);
                        } else {
                            memset(stretched, 0, npix);
                        }
                    }
                    else if (bytes == 2) {
                        const guint16 *p = raw;
                        guint16 minv = USHRT_MAX, maxv = 0;
                        for (guint i = 0; i < npix; i++) {
                            if (p[i] < minv) minv = p[i];
                            if (p[i] > maxv) maxv = p[i];
                        }
                        if (maxv > minv) {
                            float scale = 255.0f / (maxv - minv);
                            for (guint i = 0; i < npix; i++)
                                stretched[i] = (guint8)((p[i] - minv) * scale + 0.5f);
                        } else {
                            memset(stretched, 0, npix);
                        }
                    }
                    else {
                        memset(stretched, 0, npix);
                    }
                    /* Convert buffer data to a Python bytes object */
                    result = PyBytes_FromStringAndSize(stretched, npix);
                    //result = PyLong_FromLong(pf);
                    free(stretched);
                }
            } else {
                result = PyUnicode_FromString("No data available");
            }
        } else {
            result = PyUnicode_FromString("Failed to acquire buffer");
        }

        /* Destroy the buffer */
        g_clear_object(&buffer);
    } else {
        result = PyUnicode_FromString("No camera found");
    }

    /* Destroy the camera instance */
    g_clear_object(&camera);

    return result;
}

static PyObject* get_camera_buffers(PyObject* self, PyObject* args) {
    const int bufferNum;
    ArvCamera *camera;
    ArvBuffer *buffer;
    GError *error = NULL;
    const void *data;
    size_t buffer_sz;
    PyObject *result;
    
    if (!PyArg_ParseTuple(args, "i", &bufferNum))
        return NULL;

    //printf("Got: %d\n", bufferNum);

    camera = arv_camera_new (NULL, &error);
    if (ARV_IS_CAMERA (camera)) {
		ArvStream *stream = NULL;

		printf ("Found camera '%s'\n", arv_camera_get_model_name (camera, NULL));

		arv_camera_set_acquisition_mode (camera, ARV_ACQUISITION_MODE_CONTINUOUS, &error);

		if (error == NULL)
			/* Create the stream object without callback */
			stream = arv_camera_create_stream (camera, NULL, NULL, &error);

		if (ARV_IS_STREAM (stream)) {
			int i;
			size_t payload;

			/* Retrieve the payload size for buffer creation */
			payload = arv_camera_get_payload (camera, &error);
			if (error == NULL) {
				/* Insert some buffers in the stream buffer pool */
				for (i = 0; i < 2; i++)
					arv_stream_push_buffer (stream, arv_buffer_new (payload, NULL));
			}

			if (error == NULL)
				/* Start the acquisition */
				arv_camera_start_acquisition (camera, &error);

			if (error == NULL) {
				/* Retrieve 10 buffers */
                // result = PyLong_FromLong(bufferNum);
				for (i = 0; i < bufferNum; i++) {
					ArvBuffer *buffer;

					buffer = arv_stream_pop_buffer (stream);
					if (ARV_IS_BUFFER (buffer)) {
                        /* Get buffer data */
                        const void *raw = arv_buffer_get_data(buffer, &buffer_sz);
                        if (raw) {
                            /* 2) Dimensions */
                            guint width  = arv_buffer_get_image_width(buffer);
                            guint height = arv_buffer_get_image_height(buffer);
                            guint npix   = width * height;

                            /* 3) Pixel format */
                            guint pf    = arv_buffer_get_image_pixel_format(buffer);
                            guint bpp   = ARV_PIXEL_FORMAT_BIT_PER_PIXEL(pf);
                            guint bytes = bpp / 8;

                            /* 4) Contrast-stretch */
                            guint8 *stretched = malloc(npix);
                            if (!stretched) {
                                g_printerr("Out of memory saving frame %lu\n",
                                        (unsigned long)frame_count);
                            } else {
                                if (bytes == 1) {
                                    const guint8 *p = raw;
                                    guint8 minv = UCHAR_MAX, maxv = 0;
                                    for (guint i = 0; i < npix; i++) {
                                        if (p[i] < minv) minv = p[i];
                                        if (p[i] > maxv) maxv = p[i];
                                    }
                                    if (maxv > minv) {
                                        float scale = 255.0f / (maxv - minv);
                                        for (guint i = 0; i < npix; i++)
                                            stretched[i] = (guint8)((p[i] - minv) * scale + 0.5f);
                                    } else {
                                        memset(stretched, 0, npix);
                                    }
                                }
                                else if (bytes == 2) {
                                    const guint16 *p = raw;
                                    guint16 minv = USHRT_MAX, maxv = 0;
                                    for (guint i = 0; i < npix; i++) {
                                        if (p[i] < minv) minv = p[i];
                                        if (p[i] > maxv) maxv = p[i];
                                    }
                                    if (maxv > minv) {
                                        float scale = 255.0f / (maxv - minv);
                                        for (guint i = 0; i < npix; i++)
                                            stretched[i] = (guint8)((p[i] - minv) * scale + 0.5f);
                                    } else {
                                        memset(stretched, 0, npix);
                                    }
                                }
                                else {
                                    memset(stretched, 0, npix);
                                }
                                /* Convert buffer data to a Python bytes object */
                                result = PyBytes_FromStringAndSize(stretched, npix);
                                //result = PyLong_FromLong(pf);
                                free(stretched);
                            }
                        } else {
                            result = PyUnicode_FromString("No data available");
                        }
						/* Display some informations about the retrieved buffer */
						// printf ("Acquired %d×%d buffer\n",
						// 	arv_buffer_get_image_width (buffer),
						// 	arv_buffer_get_image_height (buffer));
						/* Don't destroy the buffer, but put it back into the buffer pool */
						arv_stream_push_buffer (stream, buffer);
					}
				}
			}

			if (error == NULL)
				/* Stop the acquisition */
				arv_camera_stop_acquisition (camera, &error);

			/* Destroy the stream object */
			g_clear_object (&stream);
		}

		/* Destroy the camera instance */
		g_clear_object (&camera);
	}

	if (error != NULL) {
		/* En error happened, display the correspdonding message */
		printf ("Error: %s\n", error->message);
        result = PyUnicode_FromString("Error");
	}

	return result;
}

static PyObject* camera_buffer_stream(PyObject* self, PyObject* args, PyObject* kwargs) {
    int bufferNum = -1; // default: infinite
    static char *kwlist[] = {"count", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|i", kwlist, &bufferNum))
        return NULL;
    GError *error = NULL;
    ArvCamera *camera = arv_camera_new(NULL, &error);
    if (!ARV_IS_CAMERA(camera)) {
        PyErr_SetString(PyExc_RuntimeError, "No camera found");
        return NULL;
    }
    ArvStream *stream = NULL;
    arv_camera_set_acquisition_mode(camera, ARV_ACQUISITION_MODE_CONTINUOUS, &error);
    if (error == NULL)
        stream = arv_camera_create_stream(camera, NULL, NULL, &error);
    if (!ARV_IS_STREAM(stream)) {
        g_clear_object(&camera);
        PyErr_SetString(PyExc_RuntimeError, "Failed to create stream");
        return NULL;
    }
    size_t payload = arv_camera_get_payload(camera, &error);
    if (error == NULL) {
        for (int i = 0; i < 2; i++)
            arv_stream_push_buffer(stream, arv_buffer_new(payload, NULL));
    }
    if (error == NULL)
        arv_camera_start_acquisition(camera, &error);
    if (error != NULL) {
        g_clear_object(&stream);
        g_clear_object(&camera);
        PyErr_SetString(PyExc_RuntimeError, error->message);
        g_error_free(error);
        return NULL;
    }
    // Get image info from first buffer
    ArvBuffer *buffer = arv_stream_pop_buffer(stream);
    if (!ARV_IS_BUFFER(buffer)) {
        g_clear_object(&stream);
        g_clear_object(&camera);
        PyErr_SetString(PyExc_RuntimeError, "Failed to get first buffer");
        return NULL;
    }
    guint width  = arv_buffer_get_image_width(buffer);
    guint height = arv_buffer_get_image_height(buffer);
    guint npix   = width * height;
    guint pf     = arv_buffer_get_image_pixel_format(buffer);
    guint bpp    = ARV_PIXEL_FORMAT_BIT_PER_PIXEL(pf);
    guint bytes  = bpp / 8;
    arv_stream_push_buffer(stream, buffer);
    // Allocate and return generator
    BufferStreamGen *gen = PyObject_New(BufferStreamGen, &BufferStreamGenType);
    if (!gen) {
        g_clear_object(&stream);
        g_clear_object(&camera);
        return NULL;
    }
    gen->camera = camera;
    gen->stream = stream;
    gen->remaining = bufferNum;
    gen->width = width;
    gen->height = height;
    gen->npix = npix;
    gen->bytes_per_pixel = bytes;
    gen->started = 1;
    return (PyObject *)gen;
}

// Method definitions
static PyMethodDef AravisMethods[] = {
    {"get_camera_buffer", get_camera_buffer, METH_NOARGS, "Get a camera buffer"},
    {"get_camera_buffers", get_camera_buffers, METH_VARARGS, "Get a camera buffer"},
    {"camera_buffer_stream", camera_buffer_stream, METH_VARARGS | METH_KEYWORDS, "Stream camera buffers as a generator"},
    {NULL, NULL, 0, NULL}  // Sentinel
};

// Module definition
static struct PyModuleDef aravismodule = {
    PyModuleDef_HEAD_INIT,
    "aravis",   // name of module
    "Python bindings for Aravis library",  // module documentation
    -1,
    AravisMethods
};

// Module initialization function
PyMODINIT_FUNC PyInit_aravis(void) {
    PyObject *m;

    m = PyModule_Create(&aravismodule);
    if (m == NULL)
        return NULL;

    // Create AravisError exception
    AravisError = PyErr_NewException("aravis.AravisError", NULL, NULL);
    Py_INCREF(AravisError);
    PyModule_AddObject(m, "AravisError", AravisError);

    return m;
} 