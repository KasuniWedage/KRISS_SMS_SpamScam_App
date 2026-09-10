package com.kriss.smsshield

import android.animation.AnimatorSet
import android.animation.ObjectAnimator
import android.app.ActivityOptions
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.animation.DecelerateInterpolator
import androidx.appcompat.app.AppCompatActivity
import com.kriss.smsshield.databinding.ActivitySplashBinding
import com.kriss.smsshield.storage.SessionManager

class SplashActivity : AppCompatActivity() {
    private lateinit var b: ActivitySplashBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivitySplashBinding.inflate(layoutInflater)
        setContentView(b.root)

        b.splashLogo.alpha = 0f
        b.splashLogo.scaleX = 0.78f
        b.splashLogo.scaleY = 0.78f
        b.splashLogo.translationY = 28f
        b.splashProgress.alpha = 0f

        AnimatorSet().apply {
            playTogether(
                ObjectAnimator.ofFloat(b.splashLogo, View.ALPHA, 0f, 1f),
                ObjectAnimator.ofFloat(b.splashLogo, View.SCALE_X, 0.78f, 1f),
                ObjectAnimator.ofFloat(b.splashLogo, View.SCALE_Y, 0.78f, 1f),
                ObjectAnimator.ofFloat(b.splashLogo, View.TRANSLATION_Y, 28f, 0f)
            )
            duration = 750L
            interpolator = DecelerateInterpolator(1.7f)
            start()
        }
        b.splashProgress.animate().alpha(1f).setStartDelay(450L).setDuration(300L).start()

        b.root.postDelayed({ openApp() }, 1450L)
    }

    private fun openApp() {
        val session = SessionManager(this)
        val destination = when {
            session.token() == null -> LoginActivity::class.java
            session.role() == "admin" -> AdminActivity::class.java
            else -> HomeActivity::class.java
        }
        val transition = ActivityOptions.makeCustomAnimation(this, android.R.anim.fade_in, android.R.anim.fade_out)
        startActivity(Intent(this, destination), transition.toBundle())
        finish()
    }
}
