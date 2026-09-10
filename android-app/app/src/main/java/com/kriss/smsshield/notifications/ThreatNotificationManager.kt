package com.kriss.smsshield.notifications

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.kriss.smsshield.HomeActivity
import com.kriss.smsshield.R
import com.kriss.smsshield.storage.SessionManager

object ThreatNotificationManager {
    private const val CHANNEL_ID = "kriss_threat_alerts"

    fun createChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= 26) {
            val manager = context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    context.getString(R.string.notification_channel_name),
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = context.getString(R.string.notification_channel_description)
                    enableVibration(true)
                }
            )
        }
    }

    fun show(context: Context, smsId: Int, label: String, confidence: Double, message: String) {
        if (!SessionManager(context).notificationsEnabled()) return
        if (label.equals("Legitimate", true) || label.equals("Safe", true)) return
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return
        if (!NotificationManagerCompat.from(context).areNotificationsEnabled()) return
        createChannel(context)
        val intent = Intent(context, HomeActivity::class.java).apply { flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP }
        val pending = PendingIntent.getActivity(context, smsId, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val title = context.getString(if (label.equals("Scam", true)) R.string.notification_scam_title else R.string.notification_spam_title)
        val localizedLabel = context.getString(if (label.equals("Scam", true)) R.string.label_scam else R.string.label_spam)
        val body = context.getString(R.string.notification_threat_body, localizedLabel, confidence)
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_shield)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText("$body\n\n${message.take(180)}"))
            .setColor(ContextCompat.getColor(context, if (label.equals("Scam", true)) R.color.danger else R.color.warning))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pending)
            .build()
        NotificationManagerCompat.from(context).notify(10_000 + smsId, notification)
    }
}
