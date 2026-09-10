package com.kriss.smsshield

import android.app.Application
import com.facebook.FacebookSdk

class KrissApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        val appId = getString(R.string.facebook_app_id).trim()
        val clientToken = getString(R.string.facebook_client_token).trim()
        if (appId.isNotBlank() && clientToken.isNotBlank()) {
            FacebookSdk.setApplicationId(appId)
            FacebookSdk.setClientToken(clientToken)
            FacebookSdk.sdkInitialize(applicationContext)
        }
    }
}
