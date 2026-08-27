package com.eva.homeassist

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.animateOffsetAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import kotlinx.coroutines.launch
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.eva.homeassist.ui.theme.HomeAssistTheme
import android.view.WindowManager
import androidx.compose.foundation.layout.Column
import androidx.compose.runtime.mutableLongStateOf
import kotlinx.coroutines.delay
import kotlin.time.Duration.Companion.milliseconds
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.sp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        enableEdgeToEdge()
        setContent {
            HomeAssistTheme {
                MainScreen()
            }
        }
    }
}

@Composable
fun MainScreen() {
    val context = LocalContext.current
    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED &&
                    ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions(),
        onResult = { permissions ->
            hasCameraPermission = permissions.values.all { it }
        }
    )

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) {
            permissionLauncher.launch(
                arrayOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)
            )
        }
    }

    var rawLookOffset by remember { mutableStateOf(Offset.Zero) }
    var isPersonDetected by remember { mutableStateOf(false) }
    var rawPersonScale by remember { mutableFloatStateOf(0f) }
    var aiMessage by remember { mutableStateOf("") }
    var isTalking by remember { mutableStateOf(false) }
    var residentStatus by remember { mutableStateOf<String?>(null) }
    var isListening by remember { mutableStateOf(false) }
    var cooldownExpiration by remember { mutableLongStateOf(0L) }
    var isCooling by remember { mutableStateOf(false) }

    val sttClient = remember { SttClient(BuildConfig.STT_URL) }
    val voiceRecorder = remember { VoiceRecorder(context) }
    val coroutineScope = rememberCoroutineScope()

    var isUploading by remember { mutableStateOf(false) }

    LaunchedEffect(hasCameraPermission) {
        if (hasCameraPermission) {
            voiceRecorder.startListening(
                isMuted = { isTalking },
                onSpeechStart = {
                    isListening = true
                },
                onSpeechEnd = { chunk ->
                    isListening = false
                    if (chunk.isNotEmpty()) {
                        coroutineScope.launch {
                            val result = sttClient.transcribeAudio(chunk)
                            if (result != null) {
                                val text = result.first
                                val audioUrl = result.second
                                val status = result.third
                                if (status != null) residentStatus = status

                                if (text.isNotBlank()) {
                                    aiMessage = "You said: $text"
                                }
                                if (audioUrl != null) {
                                    AudioPlayer.play(
                                        url = audioUrl,
                                        onStart = { isTalking = true },
                                        onComplete = { isTalking = false }
                                    )
                                }
                            }
                        }
                    }
                }
            )
        }
    }

    val animatedLookOffset by animateOffsetAsState(
        targetValue = rawLookOffset,
        animationSpec = spring(dampingRatio = 0.7f, stiffness = Spring.StiffnessLow),
        label = "eyeTrackingAnimation"
    )

    LaunchedEffect(cooldownExpiration) {
        val now = System.currentTimeMillis()
        if (cooldownExpiration > now) {
            isCooling = true
            delay((cooldownExpiration - now).milliseconds)
            isCooling = false
        } else {
            isCooling = false
        }
    }

    LaunchedEffect(Unit) {
        while (true) {
            delay(30_000)
            try {
                val statusData = pollStatus(BuildConfig.STATUS_URL, BuildConfig.LOCATION_NAME)
                if (statusData != null) {
                    if (statusData.status != null) residentStatus = statusData.status
                    if (statusData.audioUrl != null) {
                        AudioPlayer.play(
                            url = statusData.audioUrl,
                            onStart = { isTalking = true },
                            onComplete = { isTalking = false }
                        )
                    }
                }
            } catch (_: Exception) {}
        }
    }

    val animatedPersonScale by animateFloatAsState(
        targetValue = rawPersonScale,
        animationSpec = spring(dampingRatio = 0.7f, stiffness = Spring.StiffnessLow),
        label = "pupilDilationAnimation"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF1E1E1E))
            .systemBarsPadding()
    ) {

        StylizedTrackingFaceBackground(
            modifier = Modifier.fillMaxSize(),
            lookOffset = animatedLookOffset,
            isPersonDetected = isPersonDetected,
            personScale = animatedPersonScale,
            isTalking = isTalking,
            isCooling = isCooling,
            isListening = isListening,
            isUploading = isUploading
        )

        Column(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 24.dp, end = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {

            Box(
                modifier = Modifier
                    .size(80.dp, 80.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.Black)
            ) {
                if (hasCameraPermission) {
                    FrontCameraPreview(
                        modifier = Modifier.fillMaxSize(),
                        onPersonDetected = { normalizedOffset, detected, scale ->
                            rawLookOffset = normalizedOffset
                            isPersonDetected = detected
                            rawPersonScale = scale
                        },
                        onInferenceResult = { resultText, audioUrl, status ->
                            aiMessage = resultText
                            if (status != null) residentStatus = status
                            if (audioUrl != null) {
                                AudioPlayer.play(
                                    url = audioUrl,
                                    onStart = { isTalking = true },
                                    onComplete = { isTalking = false }
                                )
                            }
                        },
                        onCooldownActivated = { newExpirationTime ->
                            cooldownExpiration = newExpirationTime
                        },
                        onUploadStateChanged = { uploading ->
                            isUploading = uploading
                        }
                    )
                } else {
                    Text(
                        "No Permission",
                        color = Color.White,
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
            }

            Text(
                text = BuildConfig.LOCATION_NAME,
                fontSize = 10.sp,
                color = Color.White,
                modifier = Modifier.padding(top = 8.dp)
            )

            residentStatus?.let { status ->
                val (displayText, statusColor) = when (status) {
                    "ok"           -> "OK" to Color(0xFF4CAF50)
                    "danger"       -> "DANGER" to Color(0xFFF44336)
                    "not_detected" -> "NOT DETECTED" to Color(0xFF9E9E9E)
                    else           -> status.uppercase() to Color(0xFF9E9E9E)
                }
                Text(
                    text = displayText,
                    fontSize = 9.sp,
                    color = statusColor,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}