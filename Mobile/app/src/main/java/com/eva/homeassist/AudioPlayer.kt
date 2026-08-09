package com.eva.homeassist

import android.media.AudioAttributes
import android.media.MediaPlayer
import android.util.Log

object AudioPlayer {
    private var mediaPlayer: MediaPlayer? = null

    fun play(url: String, onStart: () -> Unit = {}, onComplete: () -> Unit = {}) {
        stop()

        try {
            mediaPlayer = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .build()
                )
                setDataSource(url)
                setOnPreparedListener {
                    it.start()
                    onStart()
                }
                setOnCompletionListener {
                    it.release()
                    mediaPlayer = null
                    onComplete()
                }
                setOnErrorListener { _, what, extra ->
                    Log.e("AudioPlayer", "Error playing audio: what=$what, extra=$extra")
                    onComplete()
                    true
                }
                prepareAsync()
            }
        } catch (e: Exception) {
            Log.e("AudioPlayer", "Failed to init MediaPlayer: ${e.message}")
            onComplete()
        }
    }

    fun stop() {
        try {
            mediaPlayer?.let {
                if (it.isPlaying) {
                    it.stop()
                }
                it.release()
            }
        } catch (e: Exception) {
            Log.e("AudioPlayer", "Error stopping player: ${e.message}")
        } finally {
            mediaPlayer = null
        }
    }
}