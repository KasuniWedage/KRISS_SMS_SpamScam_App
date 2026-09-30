plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.gms.google-services")
}

val backendEnvFile = rootProject.file("../backend/.env")
val backendEnv = if (backendEnvFile.exists()) {
    backendEnvFile.readLines()
        .map { it.trim() }
        .filter { it.isNotEmpty() && !it.startsWith("#") && it.contains("=") }
        .associate { line ->
            val (key, value) = line.split("=", limit = 2)
            key.trim() to value.trim()
        }
} else {
    emptyMap()
}
val facebookAppId = backendEnv["FACEBOOK_APP_ID"].orEmpty()
val facebookClientToken = backendEnv["FACEBOOK_CLIENT_TOKEN"].orEmpty()
val googleWebClientId = backendEnv["GOOGLE_OAUTH_CLIENT_ID"].orEmpty()
val releaseApiBaseUrl = backendEnv["ANDROID_API_BASE_URL"].orEmpty()

android {
    namespace = "com.kriss.smsshield"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.kriss.smsshield"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
        resValue("string", "facebook_app_id", facebookAppId)
        resValue("string", "facebook_client_token", facebookClientToken)
        resValue("string", "fb_login_protocol_scheme", "fb$facebookAppId")
        resValue("string", "google_web_client_id", googleWebClientId)
    }
    signingConfigs {
        getByName("debug") {
            storeFile = rootProject.file("kriss-debug.keystore")
            storePassword = "android"
            keyAlias = "krissdebugkey"
            keyPassword = "android"
        }
    }
    buildTypes {
        debug {
            resValue("string", "api_base_url", "http://10.0.2.2:8000/")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            val safeUrl = releaseApiBaseUrl.ifBlank { "https://invalid.invalid/" }
            resValue("string", "api_base_url", safeUrl)
        }
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { viewBinding = true }
}

tasks.matching { it.name.contains("Release", ignoreCase = true) }.configureEach {
    doFirst {
        require(releaseApiBaseUrl.startsWith("https://") && !releaseApiBaseUrl.contains("invalid.invalid")) {
            "ANDROID_API_BASE_URL must be a real HTTPS URL before building a release"
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.core:core-splashscreen:1.0.1")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.6.2")
    implementation("androidx.activity:activity-ktx:1.8.2")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.drawerlayout:drawerlayout:1.2.0")
    implementation("androidx.security:security-crypto:1.0.0")
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.11.0")
    // Google Sign-In
    implementation("com.google.android.gms:play-services-auth:21.2.0")
    // Facebook Login
    implementation("com.facebook.android:facebook-login:17.0.0")
    // Firebase (BoM manages consistent versions for all firebase-* libs below)
    implementation(platform("com.google.firebase:firebase-bom:33.1.2"))
    implementation("com.google.firebase:firebase-auth-ktx")
    // Bridges Firebase's Task<T> to Kotlin coroutines' suspend/.await()
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.8.1")
    // Charts for the analytics dashboard
    implementation("com.github.PhilJay:MPAndroidChart:v3.1.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20231013")
}