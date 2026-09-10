package com.kriss.smsshield.api

import android.content.Context
import android.content.pm.ApplicationInfo
import com.google.gson.FieldNamingPolicy
import com.google.gson.GsonBuilder
import com.kriss.smsshield.R
import com.kriss.smsshield.storage.SessionManager
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private var service:ApiService?=null
    fun api(context:Context):ApiService {
        if(service==null){
            val session=SessionManager(context)
            val isDebuggable = context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0
            val logging=HttpLoggingInterceptor().apply {
                level = if (isDebuggable) HttpLoggingInterceptor.Level.BASIC else HttpLoggingInterceptor.Level.NONE
                redactHeader("Authorization")
                redactHeader("Cookie")
            }
            val client=OkHttpClient.Builder().addInterceptor { chain ->
                val token=session.token(); val builder=chain.request().newBuilder()
                if(!token.isNullOrBlank()) builder.addHeader("Authorization","Bearer $token")
                chain.proceed(builder.build())
            }.addInterceptor(logging).build()
            val gson=GsonBuilder().setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES).create()
            service=Retrofit.Builder().baseUrl(context.getString(R.string.api_base_url)).client(client).addConverterFactory(GsonConverterFactory.create(gson)).build().create(ApiService::class.java)
        }
        return service!!
    }
}
