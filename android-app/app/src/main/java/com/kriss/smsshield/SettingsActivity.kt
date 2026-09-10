package com.kriss.smsshield

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.ArrayAdapter
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.app.ActivityCompat
import androidx.core.os.LocaleListCompat
import androidx.lifecycle.lifecycleScope
import com.kriss.smsshield.api.AuthGuard
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivitySettingsBinding
import com.kriss.smsshield.model.SettingsUpdate
import com.kriss.smsshield.storage.SessionManager
import kotlinx.coroutines.launch

class SettingsActivity : AppCompatActivity() {
    private lateinit var b: ActivitySettingsBinding
    private val languageCodes = listOf("en", "si", "ta")

    override fun onCreate(s: Bundle?) {
        super.onCreate(s)
        b = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(b.root)
        b.settingsBackIcon.setOnClickListener { finish() }
        b.languageSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, langs)
        b.accountButton.setOnClickListener { startActivity(Intent(this, AccountSettingsActivity::class.java)) }
        b.guideButton.setOnClickListener { startActivity(Intent(this, GuideActivity::class.java)) }
        load()
        b.saveButton.setOnClickListener { save() }
    }

    private val langs
        get() = listOf(
            getString(R.string.language_english),
            getString(R.string.language_sinhala),
            getString(R.string.language_tamil)
        )

    private fun load() {
        lifecycleScope.launch {
            try {
                val r = RetrofitClient.api(this@SettingsActivity).settings()
                if (r.code() == 401) {
                    AuthGuard.redirectToLogin(this@SettingsActivity)
                    return@launch
                }
                r.body()?.let {
                    val code = when (it.languagePreference.lowercase()) {
                        "sinhala", "si" -> "si"
                        "tamil", "ta" -> "ta"
                        else -> "en"
                    }
                    b.languageSpinner.setSelection(languageCodes.indexOf(code).coerceAtLeast(0))
                    b.notificationSwitch.isChecked = it.notificationsEnabled
                    b.autoDeleteSwitch.isChecked = it.autoDeleteHistory
                    SessionManager(this@SettingsActivity).saveNotificationsEnabled(it.notificationsEnabled)
                }
            } catch (_: Exception) {}
        }
    }

    private fun save() {
        val code = languageCodes[b.languageSpinner.selectedItemPosition]
        val backendLanguage = when (code) {
            "si" -> "Sinhala"
            "ta" -> "Tamil"
            else -> "English"
        }
        lifecycleScope.launch {
            try {
                val r = RetrofitClient.api(this@SettingsActivity).updateSettings(
                    SettingsUpdate(backendLanguage, b.notificationSwitch.isChecked, b.autoDeleteSwitch.isChecked)
                )
                if (r.code() == 401) {
                    AuthGuard.redirectToLogin(this@SettingsActivity)
                    return@launch
                }
                if (r.isSuccessful) {
                    SessionManager(this@SettingsActivity).saveNotificationsEnabled(b.notificationSwitch.isChecked)
                    if (b.notificationSwitch.isChecked && Build.VERSION.SDK_INT >= 33 &&
                        checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
                    ) {
                        ActivityCompat.requestPermissions(
                            this@SettingsActivity,
                            arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                            701
                        )
                    }
                    b.messageText.setText(R.string.settings_saved)
                    AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(code))
                } else {
                    b.messageText.setText(R.string.settings_failed)
                }
            } catch (e: Exception) {
                b.messageText.setText(R.string.connection_error)
            }
        }
    }
}
