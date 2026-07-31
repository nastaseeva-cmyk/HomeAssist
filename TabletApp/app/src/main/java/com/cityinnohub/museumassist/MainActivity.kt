package com.cityinnohub.museumassist

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Paint
import android.os.Bundle
import android.util.Log
import android.view.ViewGroup
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.cityinnohub.museumassist.ui.theme.MuseumAssistTheme
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import java.util.concurrent.Executors

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MuseumAssistTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    CameraScreen()
                }
            }
        }
    }
}

@Composable
fun CameraScreen() {
    val context = LocalContext.current
    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current

    var hasCameraPermission by remember { mutableStateOf(ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) }
    var detections by remember { mutableStateOf(emptyList<DetectionResult>()) }

    // Face locking states
    var targetFaceId by remember { mutableStateOf<Int?>(null) }
    var lockStartTime by remember { mutableLongStateOf(0L) }
    var isLocked by remember { mutableStateOf(false) }
    var currentTime by remember { mutableLongStateOf(System.currentTimeMillis()) }

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted -> hasCameraPermission = granted }

    LaunchedEffect(detections) {
        if (detections.isEmpty()) {
            targetFaceId = null
            lockStartTime = 0L
            isLocked = false
        } else {
            val currentTarget = detections.find { it.classId == targetFaceId }
            if (currentTarget == null) {
                val newTarget = detections.first()
                targetFaceId = newTarget.classId
                lockStartTime = System.currentTimeMillis()
                isLocked = false
            } else {
                currentTime = System.currentTimeMillis()
                if (!isLocked && currentTime - lockStartTime >= 3000) {
                    isLocked = true
                }
            }
        }
    }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) permissionLauncher.launch(Manifest.permission.CAMERA)
    }

    if (hasCameraPermission) {
        val analyzer = remember {
            FaceAnalyzer(
                onResult = { results -> detections = results },
                onImageCaptured = { bytes ->
                    uploadImage(bytes)
                }
            )
        }
        val cameraExecutor = remember { Executors.newSingleThreadExecutor() }

        LaunchedEffect(isLocked) {
            if (isLocked) {
                analyzer.requestCapture()
            }
        }

        DisposableEffect(Unit) {
            onDispose {
                cameraExecutor.shutdown()
                analyzer.close()
            }
        }

        Box(modifier = Modifier.fillMaxSize()) {
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { ctx ->
                    val previewView = PreviewView(ctx).apply { layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT) }
                    val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)

                    cameraProviderFuture.addListener({
                        val cameraProvider = cameraProviderFuture.get()
                        val preview = Preview.Builder().build().also { it.surfaceProvider =
                            previewView.surfaceProvider }
                        val imageAnalysis = ImageAnalysis.Builder()
                            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                            .build().also {
                                it.setAnalyzer(cameraExecutor, analyzer)
                            }

                        try {
                            cameraProvider.unbindAll()
                            cameraProvider.bindToLifecycle(lifecycleOwner, CameraSelector.DEFAULT_BACK_CAMERA, preview, imageAnalysis)
                        } catch (exc: Exception) {
                            Log.e("CameraX", "Binding failed", exc)
                        }
                    }, ContextCompat.getMainExecutor(ctx))
                    previewView
                }
            )

            Canvas(modifier = Modifier.fillMaxSize()) {
                val canvasWidth = size.width
                val canvasHeight = size.height

                detections.forEach { det ->
                    val left = (1f - det.xMax) * canvasWidth
                    val right = (1f - det.xMin) * canvasWidth
                    val top = det.yMin * canvasHeight
                    val bottom = det.yMax * canvasHeight

                    val isTarget = det.classId == targetFaceId
                    val elapsed = if (isTarget) currentTime - lockStartTime else 0L

                    // Green for detection, Blue when locking in (after 500ms stable detection)
                    val rectColor = when {
                        !isTarget -> Color.Green
                        elapsed < 500 -> Color.Green
                        else -> Color.Blue
                    }

                    drawRect(
                        color = rectColor,
                        topLeft = Offset(left, top),
                        size = Size(right - left, bottom - top),
                        style = Stroke(width = 8f)
                    )

                    val textPaint = Paint().apply {
                        color = if (rectColor == Color.Blue) android.graphics.Color.BLUE else android.graphics.Color.GREEN
                        textSize = 60f
                    }

                    drawContext.canvas.nativeCanvas.drawText(
                        if (isTarget && isLocked) "LOCKED" else "${det.classId}",
                        left,
                        top - 20f,
                        textPaint
                    )
                }
            }

            Button(
                onClick = { analyzer.requestCapture() },
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 32.dp)
            ) {
                Text(text = "Take Picture")
            }
        }
    } else {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(text = "Waiting for camera permissions...")
        }
    }
}

private fun uploadImage(bytes: ByteArray) {
    val client = OkHttpClient()
    val requestBody = bytes.toRequestBody("image/jpeg".toMediaTypeOrNull())
    val request = Request.Builder()
        .url("http://192.168.64.145:7000/detection")
        .post(requestBody)
        .build()

    client.newCall(request).enqueue(object : Callback {
        override fun onFailure(call: Call, e: IOException) {
            Log.e("Upload", "Failed to upload image", e)
        }

        override fun onResponse(call: Call, response: Response) {
            if (response.isSuccessful) {
                Log.d("Upload", "Successfully uploaded image")
            } else {
                Log.e("Upload", "Failed to upload image: ${response.code}")
            }
            response.close()
        }
    })
}