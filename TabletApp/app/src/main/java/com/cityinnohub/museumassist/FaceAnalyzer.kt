package com.cityinnohub.museumassist

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.Rect
import android.graphics.YuvImage
import android.util.Log
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import java.io.ByteArrayOutputStream


data class DetectionResult(
    val xMin: Float, val yMin: Float,
    val xMax: Float, val yMax: Float,
    val score: Float, val classId: Int
)

class FaceAnalyzer(
    private val onResult: (List<DetectionResult>) -> Unit,
    private val onImageCaptured: (ByteArray) -> Unit
) : ImageAnalysis.Analyzer {

    private val detector = FaceDetection.getClient(
        FaceDetectorOptions.Builder()
            .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST)
            .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_NONE)
            .setClassificationMode(FaceDetectorOptions.CLASSIFICATION_MODE_NONE)
            .setContourMode(FaceDetectorOptions.CONTOUR_MODE_NONE)
            .setMinFaceSize(0.1f)
            .enableTracking()
            .build()
    )

    private var captureRequested = false

    fun requestCapture() {
        captureRequested = true
    }

    @androidx.camera.core.ExperimentalGetImage
    override fun analyze(imageProxy: ImageProxy) {
        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val rotation = imageProxy.imageInfo.rotationDegrees

        if (captureRequested) {
            captureRequested = false
            val bytes = imageProxy.toJpeg(rotation)
            if (bytes != null) {
                onImageCaptured(bytes)
            }
        }

        val image = InputImage.fromMediaImage(mediaImage, rotation)

        val swapped = rotation == 90 || rotation == 270
        val srcW = (if (swapped) mediaImage.height else mediaImage.width).toFloat()
        val srcH = (if (swapped) mediaImage.width else mediaImage.height).toFloat()

        detector.process(image)
            .addOnSuccessListener { faces ->
                onResult(faces.map { f ->
                    DetectionResult(
                        xMin = f.boundingBox.left / srcW,
                        yMin = f.boundingBox.top / srcH,
                        xMax = f.boundingBox.right / srcW,
                        yMax = f.boundingBox.bottom / srcH,
                        score = 1f,
                        classId = f.trackingId ?: 0
                    )
                })
            }
            .addOnFailureListener { Log.e("FaceAnalyzer", "detect failed", it) }
            .addOnCompleteListener { imageProxy.close() }
    }

    fun close() = detector.close()
}

fun ImageProxy.toJpeg(rotationDegrees: Int): ByteArray? {
    val yBuffer = planes[0].buffer
    val uBuffer = planes[1].buffer
    val vBuffer = planes[2].buffer

    val ySize = yBuffer.remaining()
    val uSize = uBuffer.remaining()
    val vSize = vBuffer.remaining()

    val nv21 = ByteArray(ySize + uSize + vSize)

    yBuffer.get(nv21, 0, ySize)
    vBuffer.get(nv21, ySize, vSize)
    uBuffer.get(nv21, ySize + vSize, uSize)

    val yuvImage = YuvImage(nv21, ImageFormat.NV21, width, height, null)
    val out = ByteArrayOutputStream()
    yuvImage.compressToJpeg(Rect(0, 0, yuvImage.width, yuvImage.height), 100, out)
    val imageBytes = out.toByteArray()

    // Decode and rotate if needed
    val bitmap = BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
    val matrix = Matrix().apply {
        postRotate(rotationDegrees.toFloat())
        // Front camera mirroring
        postScale(-1f, 1f)
    }
    
    val rotatedBitmap = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    val rotatedOut = ByteArrayOutputStream()
    rotatedBitmap.compress(Bitmap.CompressFormat.JPEG, 100, rotatedOut)
    
    bitmap.recycle()
    rotatedBitmap.recycle()
    
    return rotatedOut.toByteArray()
}