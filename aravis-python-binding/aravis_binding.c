#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <aravis-0.8/arv.h>
#include <stdlib.h>
#include <stdio.h>

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

// Method definitions
static PyMethodDef AravisMethods[] = {
    {"get_camera_buffer", get_camera_buffer, METH_NOARGS, "Get a camera buffer"},
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