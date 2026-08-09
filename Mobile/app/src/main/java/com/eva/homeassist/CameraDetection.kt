package com.eva.homeassist

import android.graphics.Bitmap
import android.graphics.Matrix
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import org.tensorflow.lite.support.image.TensorImage
import org.tensorflow.lite.task.vision.detector.ObjectDetector
import java.util.concurrent.Executors
import kotlin.math.max

data class DetectedObjectState(
    val boundingBox: android.graphics.RectF,
    val label: String
)

@Composable
fun FrontCameraPreview(
    modifier: Modifier = Modifier,
    onPersonDetected: (Offset, Boolean, Float) -> Unit,
    onInferenceResult: (String, String?) -> Unit
) {
    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current

    var detectedObjects by remember { mutableStateOf(emptyList<DetectedObjectState>()) }
    var imageWidth by remember { mutableIntStateOf(1) }
    var imageHeight by remember { mutableIntStateOf(1) }

    val uploadState = remember { DetectionUploadState() }

    Box(modifier = modifier) {
        AndroidView(
            factory = { context ->
                val previewView = PreviewView(context)
                previewView.scaleType = PreviewView.ScaleType.FILL_CENTER

                val cameraProviderFuture = ProcessCameraProvider.getInstance(context)

                cameraProviderFuture.addListener({
                    val cameraProvider = cameraProviderFuture.get()
                    val preview = Preview.Builder().build().also {
                        it.surfaceProvider = previewView.surfaceProvider
                    }

                    val options = ObjectDetector.ObjectDetectorOptions.builder()
                        .setMaxResults(5)
                        .setScoreThreshold(0.5f)
                        .build()
                    val objectDetector = ObjectDetector.createFromFileAndOptions(context, "efficientdet.tflite", options)

                    val executor = Executors.newSingleThreadExecutor()

                    val imageAnalysis = ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build()

                    imageAnalysis.setAnalyzer(executor) { imageProxy ->
                        val rotationDegrees = imageProxy.imageInfo.rotationDegrees
                        val bitmap = imageProxy.toBitmap()

                        val matrix = Matrix().apply { postRotate(rotationDegrees.toFloat()) }
                        val rotatedBitmap = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)

                        imageWidth = rotatedBitmap.width
                        imageHeight = rotatedBitmap.height
                        val tensorImage = TensorImage.fromBitmap(rotatedBitmap)

                        try {
                            val results = objectDetector.detect(tensorImage)
                            detectedObjects = results.map { detection ->
                                DetectedObjectState(
                                    boundingBox = detection.boundingBox,
                                    label = detection.categories.firstOrNull()?.label ?: "Unknown"
                                )
                            }

                            val person = results.firstOrNull { it.categories.firstOrNull()?.label?.equals("person", ignoreCase = true) == true }
                            val currentTime = System.currentTimeMillis()

                            if (person != null) {
                                uploadState.isPresent = true

                                uploadState.isPresent = true

                                if (!uploadState.hasUploadedCurrentSession && currentTime >= uploadState.cooldownUntil) {
                                    uploadState.hasUploadedCurrentSession = true

                                    uploadImageToBackend(rotatedBitmap) { resultText, audioUrl ->
                                        onInferenceResult(resultText, audioUrl)
                                    }
                                }

                                val rect = person.boundingBox
                                val cx = (rect.left + rect.right) / 2f
                                val cy = (rect.top + rect.bottom) / 2f

                                val rawNormX = cx / imageWidth
                                val screenNormX = (1f - rawNormX) * 2f - 1f
                                val screenNormY = (cy / imageHeight) * 2f - 1f
                                val verticalScale = rect.height() / imageHeight.toFloat()

                                onPersonDetected(Offset(screenNormX, screenNormY), true, verticalScale)
                            } else {
                                if (uploadState.isPresent) {
                                    uploadState.isPresent = false
                                    if (uploadState.hasUploadedCurrentSession) {
                                        uploadState.cooldownUntil = currentTime + COOLDOWN_TIME_MS
                                        uploadState.hasUploadedCurrentSession = false
                                    }
                                }
                                onPersonDetected(Offset.Zero, false, 0f)
                            }
                        } catch (e: Exception) {
                            e.printStackTrace()
                        } finally {
                            imageProxy.close()
                        }
                    }

                    val cameraSelector = CameraSelector.DEFAULT_FRONT_CAMERA
                    try {
                        cameraProvider.unbindAll()
                        cameraProvider.bindToLifecycle(lifecycleOwner, cameraSelector, preview, imageAnalysis)
                    } catch (exc: Exception) {
                        exc.printStackTrace()
                    }
                }, ContextCompat.getMainExecutor(context))

                previewView
            },
            modifier = Modifier.fillMaxSize()
        )

        Canvas(modifier = Modifier.fillMaxSize()) {
            val canvasWidth = size.width
            val canvasHeight = size.height
            if (imageWidth == 1 || imageHeight == 1) return@Canvas

            val scaleX = canvasWidth / imageWidth.toFloat()
            val scaleY = canvasHeight / imageHeight.toFloat()
            val scale = max(scaleX, scaleY)
            val offsetX = (canvasWidth - imageWidth * scale) / 2f
            val offsetY = (canvasHeight - imageHeight * scale) / 2f

            val paint = android.graphics.Paint().apply {
                color = android.graphics.Color.GREEN
                textSize = 30f
            }

            detectedObjects.forEach { obj ->
                if (obj.label == "person") {
                    val rect = obj.boundingBox
                    val mappedLeft = canvasWidth - (rect.right * scale + offsetX)
                    val mappedTop = rect.top * scale + offsetY
                    val mappedRight = canvasWidth - (rect.left * scale + offsetX)
                    val mappedBottom = rect.bottom * scale + offsetY

                    drawRect(
                        color = Color.Green,
                        topLeft = Offset(mappedLeft, mappedTop),
                        size = Size(mappedRight - mappedLeft, mappedBottom - mappedTop),
                        style = Stroke(width = 5f)
                    )
                    drawContext.canvas.nativeCanvas.drawText(obj.label, mappedLeft, mappedTop - 10f, paint)
                }
            }
        }
    }
}