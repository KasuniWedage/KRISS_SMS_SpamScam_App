package com.kriss.smsshield

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.kriss.smsshield.databinding.ActivityGuideBinding
import com.kriss.smsshield.storage.SessionManager

class GuideActivity : AppCompatActivity() {
    private lateinit var binding: ActivityGuideBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityGuideBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.continueButton.setOnClickListener {
            getSharedPreferences("kriss_onboarding", MODE_PRIVATE)
                .edit().putBoolean("completed", true).apply()
            if (SessionManager(this).token() == null) {
                startActivity(Intent(this, LoginActivity::class.java))
            }
            finish()
        }
    }
}
