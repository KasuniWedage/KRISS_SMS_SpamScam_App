package com.kriss.smsshield

import android.os.Bundle
import android.content.Intent
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import androidx.recyclerview.widget.LinearLayoutManager
import com.kriss.smsshield.adapter.HistoryAdapter
import com.kriss.smsshield.api.AuthGuard
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityHistoryBinding
import com.kriss.smsshield.model.HistoryItem
import com.kriss.smsshield.report.AnalysisPdfReport
import com.kriss.smsshield.report.AnalysisReportData
import kotlinx.coroutines.launch

class HistoryActivity : AppCompatActivity() {
    private lateinit var b: ActivityHistoryBinding
    private lateinit var adapter: HistoryAdapter
    private var currentItems: List<HistoryItem> = emptyList()
    private var activeFilter: String? = null // null = All
    private var selectedReport: AnalysisReportData? = null

    private val createPdf = registerForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) { uri ->
        val report = selectedReport
        if (uri != null && report != null) {
            try {
                contentResolver.openOutputStream(uri)?.use { AnalysisPdfReport.write(this@HistoryActivity, report, it) }
                    ?: error("Unable to open destination")
                Toast.makeText(this, R.string.pdf_saved, Toast.LENGTH_LONG).show()
            } catch (_: Exception) {
                Toast.makeText(this, R.string.pdf_failed, Toast.LENGTH_LONG).show()
            }
        }
        selectedReport = null
    }

    private val createCsv = registerForActivityResult(ActivityResultContracts.CreateDocument("text/csv")) { uri ->
        if (uri != null) {
            try {
                contentResolver.openOutputStream(uri)?.bufferedWriter(Charsets.UTF_8)?.use { w ->
                    w.appendLine("sms_id,message,language,label,confidence,scam_type,created_at")
                    currentItems.forEach { x ->
                        fun esc(value: String) = "\"${value.replace("\"", "\"\"").replace("\n", " ")}\""
                        w.appendLine(listOf(x.smsId.toString(), esc(x.message), esc(x.language), esc(x.label), x.confidence.toString(), esc(x.scamType ?: ""), esc(x.createdAt)).joinToString(","))
                    }
                }
                showEmpty(getString(R.string.csv_saved))
            } catch (_: Exception) {
                showEmpty(getString(R.string.csv_failed))
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityHistoryBinding.inflate(layoutInflater)
        setContentView(b.root)
        adapter = HistoryAdapter(emptyList(), { downloadReport(it) }, { confirmDelete(it) })
        b.historyList.layoutManager = LinearLayoutManager(this)
        b.historyList.adapter = adapter

        b.historyBackIcon.setOnClickListener { finish() }
        b.batchHistoryButton.setOnClickListener { startActivity(Intent(this, BatchHistoryActivity::class.java)) }
        b.searchInputLayout.setEndIconOnClickListener { load(b.searchInput.text.toString().trim().ifBlank { null }) }
        b.searchInput.setOnEditorActionListener { _, _, _ ->
            load(b.searchInput.text.toString().trim().ifBlank { null }); true
        }
        b.exportButton.setOnClickListener {
            if (currentItems.isEmpty()) {
                showEmpty(getString(R.string.csv_no_records))
            } else createCsv.launch("kriss_sms_history.csv")
        }
        b.clearHistoryButton.setOnClickListener { showDeleteCategoryDialog() }

        b.filterChips.setOnCheckedStateChangeListener { _, checkedIds ->
            activeFilter = when (checkedIds.firstOrNull()) {
                b.chipLegit.id -> "Legitimate"
                b.chipSpam.id -> "Spam"
                b.chipScam.id -> "Scam"
                else -> null
            }
            applyFilter()
        }

        load(null)
    }

    private fun load(q: String?) {
        b.loading.visibility = View.VISIBLE
        b.emptyState.visibility = View.GONE
        lifecycleScope.launch {
            try {
                val r = RetrofitClient.api(this@HistoryActivity).history(q)
                if (r.code() == 401) {
                    AuthGuard.redirectToLogin(this@HistoryActivity)
                    return@launch
                }
                currentItems = r.body().orEmpty()
                applyFilter()
            } catch (_: Exception) {
                currentItems = emptyList()
                adapter.submit(currentItems)
                showEmpty(getString(R.string.history_load_failed))
            } finally {
                b.loading.visibility = View.GONE
            }
        }
    }

    private fun applyFilter() {
        val filtered = if (activeFilter == null) currentItems else currentItems.filter { it.label.equals(activeFilter, true) }
        adapter.submit(filtered)
        if (filtered.isEmpty()) showEmpty(getString(R.string.history_empty)) else b.emptyState.visibility = View.GONE
    }

    private fun showEmpty(message: String) {
        b.emptyText.text = message
        b.emptyState.visibility = View.VISIBLE
    }

    private fun downloadReport(item: HistoryItem) {
        val baseReport = AnalysisReportData(
            smsId = item.smsId,
            label = item.label,
            confidence = item.confidence,
            detectedLanguage = item.language,
            scamType = item.scamType,
            explanation = item.explanation,
            message = item.message,
            sender = null,
            ruleOverride = false
        )
        val languages = arrayOf(getString(R.string.language_english), getString(R.string.language_sinhala))
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.choose_report_language)
            .setItems(languages) { _, index ->
                selectedReport = baseReport.copy(reportLanguage = if (index == 1) "si" else "en")
                val date = item.createdAt.take(10).replace("-", "")
                createPdf.launch("KRISS-SMS-Report-${item.smsId}-$date.pdf")
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }

    private fun confirmDelete(x: HistoryItem) {
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.delete_history_title)
            .setMessage(R.string.delete_history_message)
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(R.string.delete) { _, _ ->
                lifecycleScope.launch {
                    try {
                        RetrofitClient.api(this@HistoryActivity).deleteHistory(x.smsId)
                        load(b.searchInput.text.toString().trim().ifBlank { null })
                    } catch (_: Exception) { }
                }
            }.show()
    }

    private fun showDeleteCategoryDialog() {
        val options = arrayOf(
            getString(R.string.delete_category_all),
            getString(R.string.delete_category_scam),
            getString(R.string.delete_category_spam),
            getString(R.string.delete_category_legit)
        )
        val categories = arrayOf<String?>(null, "Scam", "Spam", "Legitimate")
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.clear_history)
            .setItems(options) { _, index ->
                confirmBulkDelete(options[index], categories[index])
            }
            .setNegativeButton(R.string.cancel, null)
            .show()
    }

    private fun confirmBulkDelete(label: String, category: String?) {
        MaterialAlertDialogBuilder(this)
            .setTitle(R.string.delete_category_title)
            .setMessage(getString(R.string.delete_category_confirm_message, label))
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(R.string.delete) { _, _ ->
                lifecycleScope.launch {
                    try {
                        val response = RetrofitClient.api(this@HistoryActivity).deleteBulkHistory(category)
                        if (response.code() == 401) {
                            AuthGuard.redirectToLogin(this@HistoryActivity)
                            return@launch
                        }
                        val count = (response.body()?.get("deleted_count") as? Number)?.toInt() ?: 0
                        Toast.makeText(this@HistoryActivity, getString(R.string.bulk_history_deleted, count), Toast.LENGTH_SHORT).show()
                        load(b.searchInput.text.toString().trim().ifBlank { null })
                    } catch (_: Exception) {
                        Toast.makeText(this@HistoryActivity, R.string.connection_error, Toast.LENGTH_SHORT).show()
                    }
                }
            }
            .show()
    }
}
