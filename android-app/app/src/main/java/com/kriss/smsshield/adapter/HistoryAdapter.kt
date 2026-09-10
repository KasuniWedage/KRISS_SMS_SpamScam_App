package com.kriss.smsshield.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.kriss.smsshield.R
import com.kriss.smsshield.databinding.ItemHistoryBinding
import com.kriss.smsshield.model.HistoryItem

class HistoryAdapter(
    private var items: List<HistoryItem>,
    private val onDownload: (HistoryItem) -> Unit,
    private val onDelete: (HistoryItem) -> Unit
) : RecyclerView.Adapter<HistoryAdapter.Holder>() {

    class Holder(val b: ItemHistoryBinding) : RecyclerView.ViewHolder(b.root)

    override fun onCreateViewHolder(p: ViewGroup, v: Int) =
        Holder(ItemHistoryBinding.inflate(LayoutInflater.from(p.context), p, false))

    override fun getItemCount() = items.size

    override fun onBindViewHolder(h: Holder, pos: Int) {
        val x = items[pos]
        val context = h.itemView.context

        val (sideColor, pillBg, textColor) = when {
            x.label.equals("Scam", true) -> Triple(R.color.danger, R.drawable.bg_pill_danger, R.color.danger)
            x.label.equals("Spam", true) -> Triple(R.color.warning, R.drawable.bg_pill_warning, R.color.warning)
            else -> Triple(R.color.success, R.drawable.bg_pill_safe, R.color.success)
        }

        h.b.sideBar.setBackgroundColor(ContextCompat.getColor(context, sideColor))
        h.b.labelChip.setBackgroundResource(pillBg)
        h.b.labelChip.setTextColor(ContextCompat.getColor(context, textColor))
        h.b.labelChip.text = when (x.label.lowercase()) {
            "scam" -> context.getString(R.string.label_scam)
            "spam" -> context.getString(R.string.label_spam)
            else -> context.getString(R.string.label_legitimate)
        }.uppercase()
        h.b.labelText.text = "%.1f%% • %s".format(x.confidence, x.language)
        h.b.messageText.text = x.message
        h.b.metaText.text = x.createdAt.replace('T', ' ').take(19)
        h.b.downloadButton.setOnClickListener { onDownload(x) }
        h.b.deleteButton.setOnClickListener { onDelete(x) }
    }

    fun submit(newItems: List<HistoryItem>) {
        items = newItems
        notifyDataSetChanged()
    }
}
