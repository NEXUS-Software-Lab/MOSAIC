"""
MOSAIC Android API taxonomies.

The metric implementation is intentionally taxonomy-driven: every API family
counted by the quality metrics is defined in this module rather than embedded
inside the counting logic.  This makes the artifact easier to audit, version,
and extend.

Dalvik class descriptors are used throughout, e.g., Landroid/app/Activity;.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, FrozenSet, Tuple

TAXONOMY_VERSION = "2026.09-publication-ready"

# ---------------------------------------------------------------------------
# Framework coupling (FC)
# ---------------------------------------------------------------------------

# FC is defined as coupling to Android platform + AndroidX framework APIs.
FRAMEWORK_PREFIXES: tuple[str, ...] = (
    "Landroid/",
    "Landroidx/",
)

# ---------------------------------------------------------------------------
# Component and UI detection seeds
# ---------------------------------------------------------------------------

FRAGMENT_BASES: frozenset[str] = frozenset({
    "Landroid/app/Fragment;",
    "Landroidx/fragment/app/Fragment;",
    "Landroid/support/v4/app/Fragment;",
    "Landroidx/fragment/app/DialogFragment;",
    "Landroidx/fragment/app/ListFragment;",
    "Landroidx/preference/PreferenceFragmentCompat;",
})

UI_BASES: frozenset[str] = FRAGMENT_BASES | frozenset({
    # Activities / modern Activity bases
    "Landroid/app/Activity;",
    "Landroid/app/ListActivity;",
    "Landroid/preference/PreferenceActivity;",
    "Landroidx/activity/ComponentActivity;",
    "Landroidx/appcompat/app/AppCompatActivity;",
    "Landroidx/fragment/app/FragmentActivity;",

    # Adapters
    "Landroid/widget/Adapter;",
    "Landroid/widget/BaseAdapter;",
    "Landroid/widget/ArrayAdapter;",
    "Landroid/widget/CursorAdapter;",
    "Landroid/widget/SimpleAdapter;",
    "Landroidx/recyclerview/widget/RecyclerView$Adapter;",
    "Landroidx/viewpager/widget/PagerAdapter;",
    "Landroidx/viewpager2/adapter/FragmentStateAdapter;",

    # Custom views and Compose-hosted views
    "Landroid/view/View;",
    "Landroid/view/ViewGroup;",
    "Landroid/view/SurfaceView;",
    "Landroid/view/TextureView;",
    "Landroid/webkit/WebView;",
    "Landroidx/compose/ui/platform/ComposeView;",
    "Landroidx/compose/ui/platform/AbstractComposeView;",
})

# Lifecycle methods explicitly implemented in component / fragment classes.
# Application-level callbacks are intentionally not included because LL is
# normalized by component/fragment lifecycle hosts, not by Application objects.
LIFECYCLE_METHODS: frozenset[str] = frozenset({
    # Activity / Fragment shared
    "onCreate",
    "onStart",
    "onResume",
    "onPause",
    "onStop",
    "onDestroy",
    "onRestart",
    "onSaveInstanceState",
    "onRestoreInstanceState",
    "onNewIntent",
    "onActivityResult",
    "onRequestPermissionsResult",
    "onWindowFocusChanged",

    # Fragment-specific
    "onAttach",
    "onCreateView",
    "onViewCreated",
    "onStart",
    "onResume",
    "onPause",
    "onStop",
    "onDestroyView",
    "onDestroy",
    "onDetach",
    "onActivityCreated",
    "onViewStateRestored",
    "onHiddenChanged",

    # Service-specific
    "onCreate",
    "onStartCommand",
    "onBind",
    "onUnbind",
    "onRebind",
    "onTaskRemoved",
    "onDestroy",

    # BroadcastReceiver
    "onReceive",
})

# ---------------------------------------------------------------------------
# ICC Coupling (IC)
# ---------------------------------------------------------------------------

# Methods counted as ICC when they are called on Android framework classes that
# dispatch to activities, services, receivers, content providers, or pending intents.
ICC_METHODS_BY_CLASS: Mapping[str, FrozenSet[str]] = {
    "Landroid/app/Activity;": frozenset({
        "startActivity",
        "startActivityForResult",
        "startActivityIfNeeded",
        "startNextMatchingActivity",
        "startActivities",
        "startIntentSender",
        "startIntentSenderForResult",
        "bindService",
        "unbindService",
        "startService",
        "stopService",
        "startForegroundService",
        "sendBroadcast",
        "sendBroadcastAsUser",
        "sendOrderedBroadcast",
        "sendOrderedBroadcastAsUser",
        "sendStickyBroadcast",
        "sendStickyBroadcastAsUser",
        "registerReceiver",
        "unregisterReceiver",
    }),
    "Landroid/app/Service;": frozenset({
        "startActivity",
        "startActivities",
        "startService",
        "stopService",
        "startForegroundService",
        "bindService",
        "unbindService",
        "sendBroadcast",
        "sendBroadcastAsUser",
        "sendOrderedBroadcast",
        "sendOrderedBroadcastAsUser",
        "sendStickyBroadcast",
        "sendStickyBroadcastAsUser",
        "registerReceiver",
        "unregisterReceiver",
    }),
    "Landroid/app/Fragment;": frozenset({
        "startActivity",
        "startActivityForResult",
        "startIntentSenderForResult",
    }),
    "Landroidx/fragment/app/Fragment;": frozenset({
        "startActivity",
        "startActivityForResult",
        "startIntentSenderForResult",
        "registerForActivityResult",
    }),
    "Landroid/support/v4/app/Fragment;": frozenset({
        "startActivity",
        "startActivityForResult",
        "startIntentSenderForResult",
    }),
    "Landroid/content/Context;": frozenset({
        "startActivity",
        "startActivities",
        "startService",
        "stopService",
        "startForegroundService",
        "bindService",
        "unbindService",
        "sendBroadcast",
        "sendBroadcastAsUser",
        "sendOrderedBroadcast",
        "sendOrderedBroadcastAsUser",
        "sendStickyBroadcast",
        "sendStickyBroadcastAsUser",
        "registerReceiver",
        "unregisterReceiver",
    }),
    "Landroid/content/ContextWrapper;": frozenset({
        "startActivity",
        "startActivities",
        "startService",
        "stopService",
        "startForegroundService",
        "bindService",
        "unbindService",
        "sendBroadcast",
        "sendBroadcastAsUser",
        "sendOrderedBroadcast",
        "sendOrderedBroadcastAsUser",
        "sendStickyBroadcast",
        "sendStickyBroadcastAsUser",
        "registerReceiver",
        "unregisterReceiver",
    }),
    "Landroidx/core/content/ContextCompat;": frozenset({
        "startActivity",
        "startActivities",
        "startForegroundService",
        "registerReceiver",
    }),
    "Landroidx/core/app/ActivityCompat;": frozenset({
        "startActivityForResult",
        "startIntentSenderForResult",
    }),
    "Landroidx/activity/result/ActivityResultLauncher;": frozenset({
        "launch",
    }),
    "Landroid/content/ContentResolver;": frozenset({
        "query",
        "insert",
        "update",
        "delete",
        "bulkInsert",
        "call",
        "applyBatch",
        "openInputStream",
        "openOutputStream",
        "openFileDescriptor",
        "openAssetFileDescriptor",
        "openTypedAssetFileDescriptor",
    }),
    "Landroid/app/PendingIntent;": frozenset({
        "getActivity",
        "getActivities",
        "getService",
        "getForegroundService",
        "getBroadcast",
        "send",
    }),
    "Landroidx/core/app/TaskStackBuilder;": frozenset({
        "startActivities",
        "getPendingIntent",
    }),
    "Landroidx/localbroadcastmanager/content/LocalBroadcastManager;": frozenset({
        "sendBroadcast",
        "sendBroadcastSync",
        "registerReceiver",
        "unregisterReceiver",
    }),
}

# ---------------------------------------------------------------------------
# Async Burden (AB)
# ---------------------------------------------------------------------------

ASYNC_EXACT_CLASSES: frozenset[str] = frozenset({
    # Java threading primitives
    "Ljava/lang/Thread;",
    "Ljava/lang/Runnable;",
    "Ljava/lang/Process;",

    # Android Handler / message system
    "Landroid/os/Handler;",
    "Landroid/os/HandlerThread;",
    "Landroid/os/Looper;",
    "Landroid/os/Message;",
    "Landroid/os/Messenger;",

    # Java timers
    "Ljava/util/Timer;",
    "Ljava/util/TimerTask;",

    # Android legacy async / background services
    "Landroid/os/AsyncTask;",
    "Landroid/app/IntentService;",

    # Android scheduling
    "Landroid/app/AlarmManager;",
    "Landroid/app/job/JobScheduler;",
    "Landroid/app/job/JobService;",
    "Landroid/app/job/JobInfo;",

    # Jetpack helpers
    "Landroidx/core/app/JobIntentService;",
})

ASYNC_PREFIXES: tuple[str, ...] = (
    # Java concurrency package: Executor, ExecutorService, Future, Callable,
    # CompletableFuture, ForkJoinPool, CountDownLatch, Semaphore, etc.
    "Ljava/util/concurrent/",

    # Kotlin coroutines
    "Lkotlinx/coroutines/",
    "Lkotlin/coroutines/",

    # RxJava / reactive chains
    "Lio/reactivex/",
    "Lrx/",

    # WorkManager and related background work
    "Landroidx/work/",
    "Landroidx/concurrent/",
    "Lcom/google/common/util/concurrent/",

    # Legacy/background schedulers sometimes seen in older APKs
    "Lcom/firebase/jobdispatcher/",
    "Lcom/google/android/gms/gcm/",
)

# Some async calls are better identified by method on otherwise broad classes.
ASYNC_METHODS_BY_CLASS: Mapping[str, FrozenSet[str]] = {
    "Landroid/view/View;": frozenset({"post", "postDelayed", "postOnAnimation", "postOnAnimationDelayed"}),
    "Landroid/os/Handler;": frozenset({"post", "postDelayed", "postAtTime", "sendMessage", "sendMessageDelayed", "sendEmptyMessage"}),
    "Landroid/app/Activity;": frozenset({"runOnUiThread"}),
}

# ---------------------------------------------------------------------------
# Platform Dependence / Platform Reliance (PD/PR)
# ---------------------------------------------------------------------------

RESOURCE_EXACT_CLASSES: frozenset[str] = frozenset({
    # Power / wake locks
    "Landroid/os/PowerManager;",
    "Landroid/os/PowerManager$WakeLock;",

    # Alarms and jobs
    "Landroid/app/AlarmManager;",
    "Landroid/app/job/JobScheduler;",
    "Landroid/app/job/JobService;",
    "Landroid/app/job/JobInfo;",
    "Landroid/app/job/JobInfo$Builder;",

    # Notifications / foreground execution
    "Landroid/app/NotificationManager;",
    "Landroid/app/Notification;",
    "Landroid/app/Notification$Builder;",
    "Landroid/app/NotificationChannel;",

    # Sensors / device resources
    "Landroid/hardware/SensorManager;",
    "Landroid/hardware/Sensor;",
    "Landroid/hardware/Camera;",
    "Landroid/media/AudioManager;",
    "Landroid/os/Vibrator;",
    "Landroid/os/VibrationEffect;",

    # Connectivity / network resources
    "Landroid/net/ConnectivityManager;",
    "Landroid/net/Network;",
    "Landroid/net/NetworkRequest;",
    "Landroid/net/NetworkCapabilities;",
    "Landroid/net/VpnService;",
    "Landroid/app/DownloadManager;",
})

RESOURCE_PREFIXES: tuple[str, ...] = (
    "Landroid/hardware/camera2/",
    "Landroidx/camera/",
    "Landroid/location/",
    "Landroid/bluetooth/",
    "Landroid/media/",
    "Landroidx/work/",
    "Landroidx/core/app/Notification",
    "Lcom/google/android/gms/location/",
    "Landroid/hardware/usb/",
    "Landroid/nfc/",
    "Landroid/net/wifi/",
    "Landroid/net/wifi/aware/",
    "Landroid/net/wifi/p2p/",
    "Landroid/telephony/",
    "Landroid/hardware/biometrics/",
    "Landroidx/biometric/",
    "Landroid/uwb/",
)

RESOURCE_METHODS_BY_CLASS: Mapping[str, FrozenSet[str]] = {
    "Landroid/app/Service;": frozenset({
        "startForeground",
        "stopForeground",
    }),
    "Landroid/content/Context;": frozenset({
        "startForegroundService",
    }),
    "Landroid/content/ContextWrapper;": frozenset({
        "startForegroundService",
    }),
    "Landroidx/core/content/ContextCompat;": frozenset({
        "startForegroundService",
    }),
    "Landroidx/core/app/ServiceCompat;": frozenset({
        "startForeground",
        "stopForeground",
    }),
}

# ---------------------------------------------------------------------------
# UI Entanglement (UE) — non-UI operation families inside UI classes
# ---------------------------------------------------------------------------

NONUI_EXACT_CLASSES: frozenset[str] = frozenset({
    # Network
    "Ljava/net/URL;",
    "Ljava/net/URI;",
    "Ljava/net/HttpURLConnection;",
    "Ljava/net/URLConnection;",
    "Ljavax/net/ssl/HttpsURLConnection;",

    # Database / local data
    "Landroid/database/sqlite/SQLiteDatabase;",
    "Landroid/database/sqlite/SQLiteOpenHelper;",
    "Landroid/database/Cursor;",
    "Landroid/content/SharedPreferences;",
    "Landroid/content/SharedPreferences$Editor;",

    # File I/O
    "Ljava/io/File;",
    "Ljava/io/FileInputStream;",
    "Ljava/io/FileOutputStream;",
    "Ljava/io/BufferedReader;",
    "Ljava/io/BufferedWriter;",
    "Landroid/os/Environment;",

    # Crypto / security
    "Ljavax/crypto/Cipher;",
    "Ljavax/crypto/Mac;",
    "Ljavax/crypto/KeyGenerator;",
    "Ljava/security/MessageDigest;",
    "Ljava/security/KeyStore;",
    "Ljava/security/SecureRandom;",

    # IPC / provider access
    "Landroid/content/ContentResolver;",
    "Landroid/app/PendingIntent;",

    # Async / concurrency representative exact classes
    "Ljava/lang/Thread;",
    "Landroid/os/Handler;",
    "Landroid/os/AsyncTask;",
    "Landroid/os/HandlerThread;",
})

NONUI_PREFIXES: tuple[str, ...] = (
    # Network stacks
    "Ljava/net/",
    "Ljavax/net/",
    "Lokhttp3/",
    "Lokhttp/",
    "Lretrofit2/",
    "Lio/ktor/",
    "Lcom/android/volley/",
    "Lokio/",
    "Lcom/squareup/okhttp/",

    # Database / persistence
    "Landroid/database/",
    "Landroidx/room/",
    "Landroidx/datastore/",
    "Lio/realm/",
    "Lnet/sqlcipher/",
    "Lcom/google/firebase/database/",
    "Lcom/google/firebase/firestore/",
    "Lcom/google/firebase/storage/",
    "Lcom/google/firebase/functions/",

    # File I/O
    "Ljava/io/",
    "Ljava/nio/",

    # Crypto / security
    "Ljavax/crypto/",
    "Ljava/security/",
    "Landroid/security/",

    # Async / concurrency
    "Ljava/util/concurrent/",
    "Lkotlinx/coroutines/",
    "Lkotlin/coroutines/",
    "Lio/reactivex/",
    "Lrx/",
    "Landroidx/work/",
    "Lcom/google/common/util/concurrent/",

    # IPC / platform data exchange
    "Landroid/content/ContentResolver",
)

NONUI_METHODS_BY_CLASS: Mapping[str, FrozenSet[str]] = {
    # WebView network/content loading from UI classes is a common entanglement signal.
    "Landroid/webkit/WebView;": frozenset({
        "loadUrl",
        "loadData",
        "loadDataWithBaseURL",
        "postUrl",
        "evaluateJavascript",
    }),
}
