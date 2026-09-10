package com.kriss.smsshield

import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.os.Environment
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.kriss.smsshield.adapter.DatasetSampleAdapter
import com.kriss.smsshield.api.RetrofitClient
import com.kriss.smsshield.databinding.ActivityDatasetAdminBinding
import com.kriss.smsshield.model.CreateVersionRequest
import com.kriss.smsshield.model.DatasetSampleItem
import com.kriss.smsshield.model.ReviewSampleRequest
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class DatasetAdminActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDatasetAdminBinding
    private lateinit var adapter: DatasetSampleAdapter
    private var currentStatusFilter: String = "all"
    private var allSamples: List<DatasetSampleItem> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDatasetAdminBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupUI()
        loadSamples()
    }

    private fun setupUI() {
        binding.btnBack.setOnClickListener { finish() }
        binding.btnRefresh.setOnClickListener { loadSamples() }
        binding.swipeRefresh.setOnRefreshListener { loadSamples() }

        adapter = DatasetSampleAdapter(
            onApproveClick = { item -> reviewSample(item, "approved") },
            onRejectClick = { item -> reviewSample(item, "rejected") }
        )
        binding.rvSamples.layoutManager = LinearLayoutManager(this)
        binding.rvSamples.adapter = adapter

        // Status Filter Chips
        binding.chipGroupStatus.setOnCheckedStateChangeListener { _, checkedIds ->
            currentStatusFilter = when {
                checkedIds.contains(R.id.chipPending) -> "pending"
                checkedIds.contains(R.id.chipApproved) -> "approved"
                checkedIds.contains(R.id.chipRejected) -> "rejected"
                else -> "all"
            }
            loadSamples()
        }

        binding.btnExportCsv.setOnClickListener { exportDatasetCsv() }
        binding.btnCreateSnapshot.setOnClickListener { showCreateSnapshotDialog() }
    }

    private fun loadSamples() {
        binding.swipeRefresh.isRefreshing = true
        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api(this@DatasetAdminActivity).adminDatasetSamples(status = currentStatusFilter, limit = 100)
                if (resp.isSuccessful && resp.body() != null) {
                    allSamples = resp.body()!!
                    adapter.submitList(allSamples)
                    updateStatsHeader(allSamples)
                    binding.layoutEmpty.visibility = if (allSamples.isEmpty()) View.VISIBLE else View.GONE
                } else {
                    Toast.makeText(this@DatasetAdminActivity, "Failed to load samples: ${resp.code()}", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@DatasetAdminActivity, "Error: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.swipeRefresh.isRefreshing = false
            }
        }
    }

    private fun updateStatsHeader(samples: List<DatasetSampleItem>) {
        val total = samples.size
        val pending = samples.count { it.status.equals("pending", ignoreCase = true) }
        val approved = samples.count { it.status.equals("approved", ignoreCase = true) }
        binding.tvDatasetStats.text = "$total samples loaded ($pending pending, $approved approved)"
    }

    private fun reviewSample(item: DatasetSampleItem, newStatus: String) {
        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api(this@DatasetAdminActivity).reviewDatasetSample(
                    sampleId = item.id,
                    body = ReviewSampleRequest(status = newStatus, reviewNote = "Reviewed via Android Admin Console")
                )
                if (resp.isSuccessful) {
                    Toast.makeText(this@DatasetAdminActivity, "Sample #${item.id} marked $newStatus", Toast.LENGTH_SHORT).show()
                    loadSamples()
                } else {
                    Toast.makeText(this@DatasetAdminActivity, "Update failed: ${resp.code()}", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@DatasetAdminActivity, "Error: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun exportDatasetCsv() {
        lifecycleScope.launch {
            try {
                Toast.makeText(this@DatasetAdminActivity, "Exporting dataset CSV...", Toast.LENGTH_SHORT).show()
                val resp = RetrofitClient.api(this@DatasetAdminActivity).exportDatasetCsv()
                if (resp.isSuccessful && resp.body() != null) {
                    val body = resp.body()!!
                    val fileName = "kriss_dataset_approved_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())}.csv"
                    val downloadsDir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS) ?: filesDir
                    val targetFile = File(downloadsDir, fileName)

                    FileOutputStream(targetFile).use { output ->
                        output.write(body.bytes())
                    }

                    Toast.makeText(this@DatasetAdminActivity, "CSV saved to: ${targetFile.name}", Toast.LENGTH_LONG).show()
                } else {
                    Toast.makeText(this@DatasetAdminActivity, "CSV export failed: ${resp.code()}", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@DatasetAdminActivity, "Export error: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showCreateSnapshotDialog() {
        val input = EditText(this)
        input.hint = "e.g. v2.1-sinhala-tamil-aug2026"
        val defaultTag = "v${SimpleDateFormat("yyyyMMdd_HHmm", Locale.US).format(Date())}"
        input.setText(defaultTag)

        AlertDialog.Builder(this)
            .setTitle("Create Dataset Version Snapshot")
            .setMessage("Freeze current approved samples into a versioned training snapshot file.")
            .setView(input)
            .setPositiveButton("Create") { _, _ ->
                val tag = input.text.toString().trim()
                if (tag.isNotEmpty()) {
                    createSnapshot(tag)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun createSnapshot(versionTag: String) {
        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api(this@DatasetAdminActivity).createDatasetVersion(CreateVersionRequest(versionTag = versionTag))
                if (resp.isSuccessful && resp.body() != null) {
                    val item = resp.body()!!
                    AlertDialog.Builder(this@DatasetAdminActivity)
                        .setTitle("Dataset Snapshot Created")
                        .setMessage("Version: ${item.versionTag}\nApproved Samples: ${item.sampleCount}\nFile: ${item.filePath}")
                        .setPositiveButton("OK", null)
                        .show()
                } else {
                    Toast.makeText(this@DatasetAdminActivity, "Snapshot failed: ${resp.code()}", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@DatasetAdminActivity, "Error: ${e.localizedMessage}", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
