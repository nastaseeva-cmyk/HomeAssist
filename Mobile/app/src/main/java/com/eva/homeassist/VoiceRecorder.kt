package com.eva.homeassist

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import com.konovalov.vad.silero.VadSilero
import com.konovalov.vad.silero.config.FrameSize
import com.konovalov.vad.silero.config.Mode
import com.konovalov.vad.silero.config.SampleRate
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream

class VoiceRecorder(
    private val context: Context,
    private val sampleRate: Int = 16000,
    private val silenceDurationMs: Long = 700
) {
    @SuppressLint("MissingPermission")
    suspend fun startListening(
        onSpeechStart: () -> Unit,
        onSpeechEnd: (ByteArray) -> Unit
    ) = withContext(Dispatchers.IO) {

        val frameSize = 512
        val bufferSize = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        ).coerceAtLeast(frameSize * 10)

        val audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize
        )

        if (audioRecord.state != AudioRecord.STATE_INITIALIZED) {
            return@withContext
        }

        val vad = VadSilero(
            context,
            SampleRate.SAMPLE_RATE_16K,
            FrameSize.FRAME_SIZE_512,
            mode = Mode.NORMAL,
            silenceDurationMs = 300,
            speechDurationMs = 50
        )

        audioRecord.startRecording()

        val shortBuffer = ShortArray(frameSize)
        var isSpeaking = false
        var silenceStartTime = 0L
        val audioStream = ByteArrayOutputStream()

        val preSpeechFrames = 10
        val preSpeechBuffer = ArrayDeque<ByteArray>(preSpeechFrames)

        try {
            while (isActive) {
                val readResult = audioRecord.read(shortBuffer, 0, frameSize)
                if (readResult == frameSize) {

                    val isSpeechDetected = vad.isSpeech(shortBuffer)

                    val currentChunkBytes = ByteArray(readResult * 2)
                    for (i in 0 until readResult) {
                        currentChunkBytes[i * 2] = (shortBuffer[i].toInt() and 0xFF).toByte()
                        currentChunkBytes[i * 2 + 1] = ((shortBuffer[i].toInt() shr 8) and 0xFF).toByte()
                    }

                    if (isSpeechDetected) {
                        if (!isSpeaking) {
                            isSpeaking = true
                            audioStream.reset()
                            for (chunk in preSpeechBuffer) {
                                audioStream.write(chunk)
                            }
                            preSpeechBuffer.clear()
                            onSpeechStart()
                        }
                        silenceStartTime = 0L
                    } else {
                        if (isSpeaking && silenceStartTime == 0L) {
                            silenceStartTime = System.currentTimeMillis()
                        }
                    }

                    if (isSpeaking) {
                        audioStream.write(currentChunkBytes)

                        if (silenceStartTime > 0 && (System.currentTimeMillis() - silenceStartTime) > silenceDurationMs) {
                            isSpeaking = false
                            silenceStartTime = 0L
                            val chunk = audioStream.toByteArray()
                            if (chunk.isNotEmpty()) {
                                onSpeechEnd(chunk)
                            }
                            audioStream.reset()

                        }
                    } else {
                        if (preSpeechBuffer.size >= preSpeechFrames) {
                            preSpeechBuffer.removeFirst()
                        }
                        preSpeechBuffer.addLast(currentChunkBytes)
                    }
                }
            }
        } finally {
            audioRecord.stop()
            audioRecord.release()
            audioStream.close()
            vad.close()
        }
    }
}