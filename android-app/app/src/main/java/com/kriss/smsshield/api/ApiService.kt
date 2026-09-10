package com.kriss.smsshield.api

import com.kriss.smsshield.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    @GET("health") suspend fun health(): HealthResponse
    @POST("api/auth/register") suspend fun register(@Body body:RegisterRequest): Response<UserDto>
    @POST("api/auth/login") suspend fun login(@Body body:LoginRequest): Response<TokenResponse>
    @POST("api/auth/logout") suspend fun logout(): Response<Map<String,String>>
    @POST("api/auth/forgot-password") suspend fun forgotPassword(@Body body:ForgotPasswordRequest): Response<MessageResponse>
    @POST("api/auth/verify-reset-code") suspend fun verifyResetCode(@Body body:VerifyResetCodeRequest): Response<MessageResponse>
    @POST("api/auth/reset-password") suspend fun resetPassword(@Body body:ResetPasswordRequest): Response<MessageResponse>
    @POST("api/auth/google") suspend fun googleLogin(@Body body:GoogleAuthRequest): Response<TokenResponse>
    @POST("api/auth/facebook") suspend fun facebookLogin(@Body body:FacebookAuthRequest): Response<TokenResponse>
    @POST("api/auth/firebase-sync") suspend fun firebaseSync(@Body body:FirebaseSyncRequest): Response<TokenResponse>
    @POST("api/classify") suspend fun classify(@Body body:ClassificationRequest): Response<ClassificationResponse>
    @POST("api/classify/batch") suspend fun classifyBatch(@Body body:BatchRequest): Response<List<ClassificationResponse>>
    @GET("api/batch/history") suspend fun getBatchHistory(@Query("limit") limit:Int=50): Response<List<BatchHistoryResponse>>
    @DELETE("api/batch/history/{batchId}") suspend fun deleteBatchHistory(@Path("batchId") batchId:String): Response<Map<String,String>>
    @DELETE("api/batch/history") suspend fun clearBatchHistory(): Response<Map<String,Any>>
    @GET("api/history") suspend fun history(@Query("q") query:String?=null, @Query("limit") limit:Int=100): Response<List<HistoryItem>>
    @DELETE("api/history/{id}") suspend fun deleteHistory(@Path("id") id:Int): Response<Map<String,String>>
    @DELETE("api/history") suspend fun deleteBulkHistory(@Query("category") category:String?=null): Response<Map<String,Any>>
    @POST("api/reports") suspend fun report(@Body body:ReportRequest): Response<Map<String,String>>
    @POST("api/feedback") suspend fun feedback(@Body body:FeedbackRequest): Response<Map<String,String>>
    @GET("api/settings") suspend fun settings(): Response<UserDto>
    @PATCH("api/settings") suspend fun updateSettings(@Body body:SettingsUpdate): Response<UserDto>
    @POST("api/community-spam") suspend fun publishSpam(@Body body:PublishSpamRequest):Response<Map<String,String>>
    @GET("api/community-spam") suspend fun communitySpam():Response<List<PublishedSpamItem>>
    @GET("api/my-reports") suspend fun myReports():Response<List<UserReportItem>>
    @GET("api/my-feedback") suspend fun myFeedback():Response<List<UserFeedbackItem>>
    @PATCH("api/profile") suspend fun updateProfile(@Body body:ProfileUpdate):Response<UserDto>
    @POST("api/change-password") suspend fun changePassword(@Body body:PasswordChange):Response<Map<String,String>>
    @HTTP(method="DELETE",path="api/account",hasBody=true) suspend fun deleteAccount(@Body body:DeleteAccountRequest):Response<Map<String,String>>
    @GET("api/activity-log") suspend fun activityLog():Response<List<ActivityLogItem>>
    @GET("api/admin/metrics") suspend fun adminMetrics():Response<AdminMetrics>
    @GET("api/admin/performance") suspend fun adminPerformance(@Query("hours") hours:Int=24):Response<AdminPerformance>
    @GET("api/admin/audit-integrity") suspend fun auditIntegrity():Response<AuditIntegrity>
    @GET("api/admin/users") suspend fun adminUsers():Response<List<AdminUserItem>>
    @PATCH("api/admin/users/{userId}/role") suspend fun updateUserRole(@Path("userId") userId:Int, @Query("role") role:String):Response<Map<String,String>>
    @GET("api/admin/backups") suspend fun listBackups():Response<List<BackupFileInfo>>
    @POST("api/admin/backup/create") suspend fun triggerBackup():Response<AdminBackupResponse>
    @POST("api/admin/backup/restore-test") suspend fun triggerRestoreTest(@Query("filename") filename:String?=null):Response<Map<String,Any>>
    @POST("api/admin/backup/restore-live") suspend fun triggerRestoreLive(@Query("filename") filename:String):Response<Map<String,Any>>
    @GET("api/admin/errors") suspend fun adminErrors(@Query("limit") limit:Int=50):Response<List<AdminErrorItem>>
    @DELETE("api/admin/errors") suspend fun clearAdminErrors():Response<Map<String,Any>>
    @GET("api/admin/dataset/samples") suspend fun adminDatasetSamples(@Query("status") status:String="all", @Query("language") language:String="all", @Query("limit") limit:Int=100):Response<List<DatasetSampleItem>>
    @PATCH("api/admin/dataset/samples/{sampleId}") suspend fun reviewDatasetSample(@Path("sampleId") sampleId:Int, @Body body:ReviewSampleRequest):Response<DatasetSampleItem>
    @GET("api/admin/dataset/export-csv") suspend fun exportDatasetCsv():Response<okhttp3.ResponseBody>
    @POST("api/admin/dataset/versions") suspend fun createDatasetVersion(@Body body:CreateVersionRequest):Response<DatasetVersionItem>
    @GET("api/admin/dataset/versions") suspend fun listDatasetVersions():Response<List<DatasetVersionItem>>
    @GET("api/admin/dataset/duplicates") suspend fun detectDatasetDuplicates():Response<List<DuplicateSampleItem>>
}
