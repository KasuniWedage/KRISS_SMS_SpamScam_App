package com.kriss.smsshield

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.GravityCompat
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.github.mikephil.charting.animation.Easing
import com.github.mikephil.charting.components.Legend
import com.github.mikephil.charting.data.PieData
import com.github.mikephil.charting.data.PieDataSet
import com.github.mikephil.charting.data.PieEntry
import com.github.mikephil.charting.formatter.ValueFormatter
import kotlin.math.roundToInt
import com.kriss.smsshield.api.AuthGuard
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityHomeBinding
import com.kriss.smsshield.model.ClassificationRequest
import com.kriss.smsshield.report.BatchHistoryStore
import com.kriss.smsshield.storage.SessionManager
import com.kriss.smsshield.notifications.ThreatNotificationManager
import kotlinx.coroutines.launch

class HomeActivity : AppCompatActivity() {
    private lateinit var b: ActivityHomeBinding
    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (!granted) {
                Toast.makeText(this, R.string.notification_permission_denied, Toast.LENGTH_LONG).show()
            }
        }

    override fun onCreate(s: Bundle?) {
        super.onCreate(s)
        b = ActivityHomeBinding.inflate(layoutInflater)
        setContentView(b.root)
        setupNotifications()
        setupChart()
        b.navigationView.menu.findItem(R.id.menuAdmin).isVisible = SessionManager(this).role() == "admin"
        refreshAll()

        b.dashboardRefresh.setOnRefreshListener { refreshAll() }
        b.menuButton.setOnClickListener { b.drawerLayout.openDrawer(GravityCompat.START) }
        b.navigationView.setNavigationItemSelectedListener { item ->
            when (item.itemId) {
                R.id.menuAnalyze -> b.messageInput.requestFocus()
                R.id.menuBatch -> startActivity(Intent(this, BatchActivity::class.java))
                R.id.menuHistory -> startActivity(Intent(this, HistoryActivity::class.java))
                R.id.menuCommunity -> openCommunity("community")
                R.id.menuReports -> openCommunity("reports")
                R.id.menuFeedback -> openCommunity("feedback")
                R.id.menuSettings -> startActivity(Intent(this, SettingsActivity::class.java))
                R.id.menuAdmin -> startActivity(Intent(this, AdminActivity::class.java))
                R.id.menuLogout -> logout()
            }
            b.drawerLayout.closeDrawer(GravityCompat.START)
            true
        }
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (b.drawerLayout.isDrawerOpen(GravityCompat.START)) b.drawerLayout.closeDrawer(GravityCompat.START)
                else { isEnabled = false; onBackPressedDispatcher.onBackPressed() }
            }
        })

        b.messageInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, st: Int, c: Int, a: Int) {}
            override fun onTextChanged(s: CharSequence?, st: Int, bf: Int, c: Int) {
                b.charCount.text = "${s?.length ?: 0} / 2000"
            }
            override fun afterTextChanged(e: Editable?) {}
        })

        b.analyzeButton.setOnClickListener { analyze() }
        b.batchButton.setOnClickListener { startActivity(Intent(this, BatchActivity::class.java)) }
        b.historyButton.setOnClickListener { startActivity(Intent(this, HistoryActivity::class.java)) }
        b.settingsButton.setOnClickListener { startActivity(Intent(this, SettingsActivity::class.java)) }
        b.communityButton.setOnClickListener { startActivity(Intent(this, CommunityActivity::class.java)) }
        b.logoutButton.setOnClickListener { logout() }
        showFirstLoginGuideIfNeeded()
    }

    private fun setupNotifications() {
        ThreatNotificationManager.createChannel(this)
        if (
            SessionManager(this).notificationsEnabled() &&
            android.os.Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, android.Manifest.permission.POST_NOTIFICATIONS) !=
            android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            notificationPermissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    private fun showFirstLoginGuideIfNeeded() {
        if (!intent.getBooleanExtra(EXTRA_SHOW_FIRST_LOGIN_GUIDE, false)) return
        val key = intent.getStringExtra(EXTRA_GUIDE_KEY) ?: "seen_default"
        getSharedPreferences("kriss_login_guides", MODE_PRIVATE).edit().putBoolean(key, true).apply()
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.first_login_guide_title)
            .setMessage(R.string.first_login_guide_message)
            .setNegativeButton(R.string.view_full_guide) { _, _ ->
                startActivity(Intent(this, GuideActivity::class.java))
            }
            .setPositiveButton(R.string.got_it, null)
            .show()
        intent.removeExtra(EXTRA_SHOW_FIRST_LOGIN_GUIDE)
    }

    companion object {
        const val EXTRA_SHOW_FIRST_LOGIN_GUIDE = "show_first_login_guide"
        const val EXTRA_GUIDE_KEY = "first_login_guide_key"
    }

    private fun openCommunity(tab:String) {
        startActivity(Intent(this, CommunityActivity::class.java).putExtra("tab", tab))
    }

    override fun onResume() {
        super.onResume()
        // Recompute stats whenever the user returns from Result/Batch/History screens
        loadDashboardStats()
    }

    private fun refreshAll() {
        checkHealth()
        loadDashboardStats()
    }

    private fun setupChart() {
        b.distributionChart.apply {
            description.isEnabled = false
            setUsePercentValues(true)
            setDrawEntryLabels(false)
            setHoleColor(Color.TRANSPARENT)
            holeRadius = 56f
            transparentCircleRadius = 60f
            setTransparentCircleColor(ContextCompat.getColor(this@HomeActivity, R.color.primary_light))
            setTransparentCircleAlpha(100)
            setDrawCenterText(true)
            setCenterTextColor(ContextCompat.getColor(this@HomeActivity, R.color.text_primary))
            setCenterTextSize(12f)
            setExtraOffsets(22f, 8f, 22f, 8f)
            legend.apply {
                verticalAlignment = Legend.LegendVerticalAlignment.BOTTOM
                horizontalAlignment = Legend.LegendHorizontalAlignment.CENTER
                orientation = Legend.LegendOrientation.HORIZONTAL
                setDrawInside(false)
                textSize = 11f
                textColor = ContextCompat.getColor(this@HomeActivity, R.color.text_primary)
                form = Legend.LegendForm.CIRCLE
                formSize = 9f
                xEntrySpace = 10f
                yEntrySpace = 4f
                isWordWrapEnabled = true
            }
        }
    }

    private fun checkHealth() {
        lifecycleScope.launch {
            try {
                val h = RetrofitClient.api(this@HomeActivity).health()
                val version = if (h.modelVersion.isNotBlank() && h.modelVersion != "not-loaded") h.modelVersion else "Linear SVM"
                b.systemStatus.text = if (h.modelReady) "System online • Model $version" else "System online • ML model not loaded"
                b.statusDot.backgroundTintList = ContextCompat.getColorStateList(this@HomeActivity, if (h.modelReady) R.color.success else R.color.warning)
            } catch (e: Exception) {
                b.systemStatus.text = "System: Offline"
                b.statusDot.backgroundTintList = ContextCompat.getColorStateList(this@HomeActivity, R.color.danger)
            }
        }
    }

    private fun loadDashboardStats() {
        lifecycleScope.launch {
            try {
                val r = RetrofitClient.api(this@HomeActivity).history(null)
                if (r.code() == 401) {
                    AuthGuard.redirectToLogin(this@HomeActivity)
                    return@launch
                }
                val items = r.body().orEmpty()
                val safeCount = items.count { it.label.equals("Legitimate", true) || it.label.equals("Safe", true) }
                val spamCount = items.count { it.label.equals("Spam", true) }
                val scamCount = items.count { it.label.equals("Scam", true) }
                val total = items.size
                val threats = spamCount + scamCount

                b.statScanned.text = total.toString()
                b.statThreats.text = threats.toString()
                b.statClean.text = safeCount.toString()

                if (total == 0) {
                    b.distributionChart.visibility = View.GONE
                    b.chartEmptyText.visibility = View.VISIBLE
                } else {
                    b.distributionChart.visibility = View.VISIBLE
                    b.chartEmptyText.visibility = View.GONE
                    renderChart(safeCount, spamCount, scamCount)
                }
            } catch (_: Exception) {
                // Keep dashboard usable even if stats can't load; analyze flow is unaffected.
            } finally {
                b.dashboardRefresh.isRefreshing = false
            }
        }
    }

    private fun renderChart(safe: Int, spam: Int, scam: Int) {
        val entries = mutableListOf<PieEntry>()
        val colors = mutableListOf<Int>()
        if (safe > 0) { entries.add(PieEntry(safe.toFloat(), getString(R.string.chart_legend_value, getString(R.string.label_legitimate), safe))); colors.add(ContextCompat.getColor(this, R.color.success)) }
        if (spam > 0) { entries.add(PieEntry(spam.toFloat(), getString(R.string.chart_legend_value, getString(R.string.label_spam), spam))); colors.add(ContextCompat.getColor(this, R.color.warning)) }
        if (scam > 0) { entries.add(PieEntry(scam.toFloat(), getString(R.string.chart_legend_value, getString(R.string.label_scam), scam))); colors.add(ContextCompat.getColor(this, R.color.danger)) }

        val dataSet = PieDataSet(entries, "").apply {
            this.colors = colors
            sliceSpace = 4f
            selectionShift = 5f
            valueTextSize = 11f
            valueTextColor = Color.WHITE
            valueTypeface = android.graphics.Typeface.DEFAULT_BOLD
            valueFormatter = object : ValueFormatter() {
                override fun getFormattedValue(value: Float): String = "${value.roundToInt()}%"
            }
        }
        b.distributionChart.centerText = getString(R.string.chart_center_total, safe + spam + scam)
        b.distributionChart.data = PieData(dataSet)
        b.distributionChart.animateY(700, Easing.EaseInOutQuad)
        b.distributionChart.invalidate()
    }

    private fun analyze() {
        val msg = b.messageInput.text.toString().trim()
        if (msg.isBlank()) { b.errorText.setText(R.string.sms_empty); return }
        if (msg.length > 2000) { b.errorText.setText(R.string.sms_too_long); return }
        b.loading.visibility = View.VISIBLE
        b.analyzeButton.isEnabled = false
        b.errorText.setText(R.string.processing_request)
        lifecycleScope.launch {
            try {
                val r = RetrofitClient.api(this@HomeActivity).classify(ClassificationRequest(msg, b.senderInput.text.toString().trim().ifBlank { null }))
                if (r.isSuccessful && r.body() != null) {
                    val x = r.body()!!
                    ThreatNotificationManager.show(this@HomeActivity, x.smsId, x.label, x.confidence, msg)
                    startActivity(Intent(this@HomeActivity, ResultActivity::class.java).apply {
                        putExtra("smsId", x.smsId)
                        putExtra("label", x.label)
                        putExtra("confidence", x.confidence)
                        putExtra("language", x.language)
                        putExtra("scamType", x.scamType)
                        putExtra("explanation", x.explanation)
                        putExtra("ruleOverride", x.ruleOverride)
                        putExtra("message", msg)
                        putExtra("sender", b.senderInput.text.toString().trim())
                    })
                    b.messageInput.text?.clear()
                    b.senderInput.text?.clear()
                    b.errorText.text = ""
                } else if (r.code() == 401) {
                    AuthGuard.redirectToLogin(this@HomeActivity)
                } else {
                    b.errorText.text = getString(R.string.analysis_failed, r.code())
                }
            } catch (e: Exception) {
                b.errorText.text = getString(R.string.backend_connection_error, e.localizedMessage.orEmpty())
            } finally {
                b.loading.visibility = View.GONE
                b.analyzeButton.isEnabled = true
            }
        }
    }

    private fun logout() {
        lifecycleScope.launch {
            try { RetrofitClient.api(this@HomeActivity).logout() } catch (_: Exception) {}
            BatchHistoryStore.clear(this@HomeActivity)
            SessionManager(this@HomeActivity).clear()
            Toast.makeText(this@HomeActivity, R.string.logout_success, Toast.LENGTH_SHORT).show()
            startActivity(Intent(this@HomeActivity, LoginActivity::class.java))
            finishAffinity()
        }
    }
}
