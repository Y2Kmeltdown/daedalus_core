#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <aravis-0.8/arv.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

static guint64 frame_count    = 0;

// Module-level variables
static PyObject* AravisError;

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
    int bufferNum;
    size_t buffer_sz;
    ArvCamera *camera;
    GError *error = NULL;
    PyObject *result_list = NULL;
    
    if (!PyArg_ParseTuple(args, "i", &bufferNum))
        return NULL;

    camera = arv_camera_new (NULL, &error);
    if (ARV_IS_CAMERA (camera)) {
        ArvStream *stream = NULL;
        printf ("Found camera '%s'\n", arv_camera_get_model_name (camera, NULL));
        arv_camera_set_acquisition_mode (camera, ARV_ACQUISITION_MODE_CONTINUOUS, &error);
        if (error == NULL)
            stream = arv_camera_create_stream (camera, NULL, NULL, &error);
        if (ARV_IS_STREAM (stream)) {
            int i;
            size_t payload;
            payload = arv_camera_get_payload (camera, &error);
            if (error == NULL) {
                for (i = 0; i < 20; i++)
                    arv_stream_push_buffer (stream, arv_buffer_new (payload, NULL));
            }
            if (error == NULL)
                arv_camera_start_acquisition (camera, &error);
            if (error == NULL) {
                result_list = PyList_New(0);
                for (i = 0; i < bufferNum; i++) {
                    ArvBuffer *buffer;
                    buffer = arv_stream_pop_buffer (stream);
                    if (ARV_IS_BUFFER (buffer)) {
                        if (arv_buffer_get_status(buffer) != ARV_BUFFER_STATUS_SUCCESS) {
                            PyList_Append(result_list, PyUnicode_FromString("Incomplete buffer"));
                            arv_stream_push_buffer(stream, buffer);
                            continue;
                        }
                        const void *raw = arv_buffer_get_data(buffer, &buffer_sz);
                        if (raw) {
                            guint width  = arv_buffer_get_image_width(buffer);
                            guint height = arv_buffer_get_image_height(buffer);
                            guint npix   = width * height;
                            guint pf    = arv_buffer_get_image_pixel_format(buffer);
                            guint bpp   = ARV_PIXEL_FORMAT_BIT_PER_PIXEL(pf);
                            guint bytes = bpp / 8;
                            guint8 *stretched = malloc(npix);
                            if (!stretched) {
                                g_printerr("Out of memory saving frame %lu\n", (unsigned long)frame_count);
                                PyList_Append(result_list, PyUnicode_FromString("Out of memory"));
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
                                PyObject *py_bytes = PyBytes_FromStringAndSize((const char *)stretched, npix);
                                PyList_Append(result_list, py_bytes);
                                Py_DECREF(py_bytes);
                                free(stretched);
                            }
                        } else {
                            PyList_Append(result_list, PyUnicode_FromString("No data available"));
                        }
                        arv_stream_push_buffer (stream, buffer);
                    } else {
                        PyList_Append(result_list, PyUnicode_FromString("Invalid buffer"));
                    }
                }
            }
            if (error == NULL)
                arv_camera_stop_acquisition (camera, &error);
            g_clear_object (&stream);
        }
        g_clear_object (&camera);
    }
    if (error != NULL) {
        printf ("Error: %s\n", error->message);
        if (!result_list) result_list = PyList_New(0);
        PyList_Append(result_list, PyUnicode_FromString("Error"));
    }
    if (!result_list) result_list = PyList_New(0);
    return result_list;
}

// Generator state struct
typedef struct {
    PyObject_HEAD
    // Add your data fields here
    int current_value;
    int iterations;
    int step;
    int is_infinite;
    // Add any other state you need
    ArvCamera *camera;
    ArvStream *stream;
} ir_buffer_stream;

// Deallocator - clean up resources
static void ir_buffer_stream_dealloc(ir_buffer_stream *self) {
    // Free any allocated memory
    if (self->stream) {
        g_clear_object (&self->stream);
    }
    if (self->camera) {
        g_clear_object (&self->camera);
    }
    
    // Call the parent deallocator
    Py_TYPE(self)->tp_free((PyObject *)self);
}

// Iterator function - called when you start iterating
static PyObject *ir_buffer_stream_iter(PyObject *self) {
    Py_INCREF(self);  // Return a new reference to self
    return self;
}

// Next function - called for each iteration
static PyObject *ir_buffer_stream_iternext(PyObject *self) {
    ir_buffer_stream *gen = (ir_buffer_stream *)self;
    size_t buffer_sz;
    GError *error = NULL;
    PyObject *result = NULL;
    
    // Check if we should stop iterating (for finite generators)
    if (!gen->is_infinite && gen->current_value >= gen->iterations) {
        return NULL;  // StopIteration
    }

    if (error == NULL) {
        ArvBuffer *buffer;

        // Pop and push a buffer to drop the data imediately and essentially switch to 30FPS
        //buffer = arv_stream_pop_buffer (gen->stream);
        //arv_stream_push_buffer(gen->stream, buffer);

        buffer = arv_stream_pop_buffer (gen->stream);
        if (ARV_IS_BUFFER (buffer)) {
            if (arv_buffer_get_status(buffer) != ARV_BUFFER_STATUS_SUCCESS) {
                arv_stream_push_buffer(gen->stream, buffer);
            }
            const void *data = arv_buffer_get_data(buffer, &buffer_sz);
            if (data) {
                guint width  = arv_buffer_get_image_width(buffer);
                guint height = arv_buffer_get_image_height(buffer);
                guint npix   = width * height;
                guint pf    = arv_buffer_get_image_pixel_format(buffer);
                guint bpp   = ARV_PIXEL_FORMAT_BIT_PER_PIXEL(pf);
                guint bytes = bpp / 8;
                guint8 *outFrame = malloc(npix);
                if (!outFrame) {
                    g_printerr("Out of memory saving frame %lu\n", (unsigned long)frame_count);
                    arv_stream_push_buffer(gen->stream, buffer);
                    return PyUnicode_FromString("Out of memory");
                } else {
                    if (bytes == 1) {
                        const guint8 *p = data;
                        guint8 minv = UCHAR_MAX, maxv = 0;
                        for (guint i = 0; i < npix; i++) {
                            if (p[i] < minv) minv = p[i];
                            if (p[i] > maxv) maxv = p[i];
                        }
                        if (maxv > minv) {
                            float scale = 255.0f / (maxv - minv);
                            for (guint i = 0; i < npix; i++)
                                outFrame[i] = (guint8)((p[i] - minv) * scale + 0.5f);
                        } else {
                            memset(outFrame, 0, npix);
                        }
                    }
                    else if (bytes == 2) {
                        const guint16 *p = data;
                        guint16 minv = USHRT_MAX, maxv = 0;
                        for (guint i = 0; i < npix; i++) {
                            if (p[i] < minv) minv = p[i];
                            if (p[i] > maxv) maxv = p[i];
                        }
                        if (maxv > minv) {
                            float scale = 255.0f / (maxv - minv);
                            for (guint i = 0; i < npix; i++)
                                outFrame[i] = (guint8)((p[i] - minv) * scale + 0.5f);
                        } else {
                            memset(outFrame, 0, npix);
                        }
                    }
                    else {
                        memset(outFrame, 0, npix);
                    }
                    result = PyBytes_FromStringAndSize((const char *)outFrame, npix);
                    free(outFrame);
                }
            } else {
                g_printerr("No data available");
                result = PyUnicode_FromString("No data available");
            }
            arv_stream_push_buffer (gen->stream, buffer);
        }
    }
    
    gen->current_value += gen->step;
    
    return result;
}

// Type definition
static PyTypeObject ir_buffer_streamType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "mymodule.ir_buffer_stream",
    .tp_basicsize = sizeof(ir_buffer_stream),
    .tp_dealloc = (destructor)ir_buffer_stream_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_iter = ir_buffer_stream_iter,
    .tp_iternext = ir_buffer_stream_iternext,
};

// Initialize the type
static int ir_buffer_streamType_init(void) {
    ir_buffer_streamType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&ir_buffer_streamType) < 0)
        return -1;
    return 0;
}



// Single factory function to create either finite or infinite generator
static PyObject* ir_buffer_streamer(PyObject* self, PyObject* args, PyObject* kwargs) {
    int start = 0;
    int step = 1;
    int record_time = -1;  // -1 indicates infinite (no max provided)
    
    // Aravis Camera Parameters
    GError *error = NULL;
    
    // Create the generator object
    ir_buffer_stream *gen = PyObject_New(ir_buffer_stream, &ir_buffer_streamType);
    if (!gen) {
        return NULL;
    }

    // Set up camera
    gen->camera = arv_camera_new (NULL, &error);
    if (ARV_IS_CAMERA (gen->camera)) {
        gen->stream = NULL;
        //ArvStream *stream = NULL;
        printf ("Found camera '%s'\n", arv_camera_get_model_name (gen->camera, NULL));
        arv_camera_set_acquisition_mode (gen->camera, ARV_ACQUISITION_MODE_CONTINUOUS, &error);
        if (error == NULL)
            gen->stream = arv_camera_create_stream (gen->camera, NULL, NULL, &error);
        if (ARV_IS_STREAM (gen->stream)) {
            int i;
            size_t payload;
            payload = arv_camera_get_payload (gen->camera, &error);
            if (error == NULL) {
                for (i = 0; i < 100; i++)
                    arv_stream_push_buffer (gen->stream, arv_buffer_new (payload, NULL));
            }
            if (error == NULL)
                arv_camera_start_acquisition (gen->camera, &error);
        }
    }
    // Initialize the generator state
    gen->current_value = start;
    gen->step = step;
    
    gen->iterations = 0;  // Not used for infinite
    gen->is_infinite = 1;
    
    
    return (PyObject *)gen;
}

// Method definitions
static PyMethodDef AravisMethods[] = {
    {"get_camera_buffer", get_camera_buffer, METH_NOARGS, "Get a camera buffer"},
    {"get_camera_buffers", get_camera_buffers, METH_VARARGS, "Get a list of camera buffers"},
    {"ir_buffer_streamer", (PyCFunction)ir_buffer_streamer, METH_VARARGS | METH_KEYWORDS, "Stream Camera Buffers sequentially to python"},
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

    // Initialize the ir_buffer_stream type
    if (ir_buffer_streamType_init() < 0)
        return NULL;

    m = PyModule_Create(&aravismodule);
    if (m == NULL)
        return NULL;

    // Create AravisError exception
    AravisError = PyErr_NewException("aravis.AravisError", NULL, NULL);
    Py_INCREF(AravisError);
    PyModule_AddObject(m, "AravisError", AravisError);

    return m;
};