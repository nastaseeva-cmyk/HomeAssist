package com.eva.homeassist

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.MultipartBody
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

private fun addWavHeader(pcmData: ByteArray, sampleRate: Int): ByteArray {
    val header = ByteArray(44)
    val totalDataLen = pcmData.size + 36
    val byteRate = sampleRate * 2 // 1 channel * 2 bytes (16-bit)

    header[0] = 'R'.code.toByte(); header[1] = 'I'.code.toByte()
    header[2] = 'F'.code.toByte(); header[3] = 'F'.code.toByte()
    header[4] = (totalDataLen and 0xff).toByte()
    header[5] = ((totalDataLen shr 8) and 0xff).toByte()
    header[6] = ((totalDataLen shr 16) and 0xff).toByte()
    header[7] = ((totalDataLen shr 24) and 0xff).toByte()
    header[8] = 'W'.code.toByte(); header[9] = 'A'.code.toByte()
    header[10] = 'V'.code.toByte(); header[11] = 'E'.code.toByte()
    header[12] = 'f'.code.toByte(); header[13] = 'm'.code.toByte()
    header[14] = 't'.code.toByte(); header[15] = ' '.code.toByte()
    header[16] = 16; header[17] = 0; header[18] = 0; header[19] = 0 // Subchunk1Size
    header[20] = 1; header[21] = 0 // PCM format
    header[22] = 1; header[23] = 0 // Mono
    header[24] = (sampleRate and 0xff).toByte()
    header[25] = ((sampleRate shr 8) and 0xff).toByte()
    header[26] = ((sampleRate shr 16) and 0xff).toByte()
    header[27] = ((sampleRate shr 24) and 0xff).toByte()
    header[28] = (byteRate and 0xff).toByte()
    header[29] = ((byteRate shr 8) and 0xff).toByte()
    header[30] = ((byteRate shr 16) and 0xff).toByte()
    header[31] = ((byteRate shr 24) and 0xff).toByte()
    header[32] = 2; header[33] = 0 // Block align
    header[34] = 16; header[35] = 0 // Bits per sample
    header[36] = 'd'.code.toByte(); header[37] = 'a'.code.toByte()
    header[38] = 't'.code.toByte(); header[39] = 'a'.code.toByte()
    header[40] = (pcmData.size and 0xff).toByte()
    header[41] = ((pcmData.size shr 8) and 0xff).toByte()
    header[42] = ((pcmData.size shr 16) and 0xff).toByte()
    header[43] = ((pcmData.size shr 24) and 0xff).toByte()

    return header + pcmData
}

private val sharedSttHttpClient by lazy {
    OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()
}

class SttClient(private val sttUrl: String) {
    suspend fun transcribeAudio(audioData: ByteArray): Triple<String, String?, String?>? = withContext(Dispatchers.IO) {
        try {
            val wavData = addWavHeader(audioData, 16000)

            val requestBody = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart(
                    "file",
                    "audio.wav",
                    wavData.toRequestBody("audio/wav".toMediaTypeOrNull())
                )
                .addFormDataPart("location", BuildConfig.LOCATION_NAME)
                .build()

            val request = Request.Builder()
                .url(sttUrl)
                .post(requestBody)
                .build()

            sharedSttHttpClient.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    val responseBody = response.body?.string() ?: "{}"
                    val json = JSONObject(responseBody)

                    if (json.has("text")) {
                        val text = json.getString("text")
                        val audioUrl = if (json.has("audio_url") && !json.isNull("audio_url")) json.getString("audio_url") else null
                        val residentStatus = if (json.has("resident_status") && !json.isNull("resident_status")) json.getString("resident_status") else null

                        return@withContext Triple(text, audioUrl, residentStatus)
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return@withContext null
    }
}
