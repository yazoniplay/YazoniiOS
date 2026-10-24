package com.nour.os

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.Drawable
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.union
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private data class NourApp(
    val name: String,
    val packageName: String,
    val icon: Drawable
)

@Composable
fun NourHomeScreen() {
    val context = androidx.compose.ui.platform.LocalContext.current
    var search by remember { mutableStateOf("") }
    var now by remember { mutableStateOf(System.currentTimeMillis()) }
    var showAllApps by remember { mutableStateOf(false) }

    val apps = remember(context.packageManager) { loadLaunchableApps(context) }
    val time = remember(now) { SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(now)) }
    val date = remember(now) {
        SimpleDateFormat("EEEE, d MMMM", Locale.getDefault()).format(Date(now))
            .replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString() }
    }

    LaunchedEffect(Unit) {
        while (true) {
            now = System.currentTimeMillis()
            delay(30_000)
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.linearGradient(
                    colors = listOf(
                        Color(0xFF101C35),
                        Color(0xFF080D1A),
                        Color(0xFF101025),
                        Color(0xFF070B13)
                    )
                )
            )
            .windowInsetsPadding(WindowInsets.statusBars.union(WindowInsets.navigationBars))
    ) {
        Box(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 60.dp, end = 12.dp)
                .size(210.dp)
                .clip(CircleShape)
                .background(Color(0x333ACFE8))
        )
        Box(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(top = 250.dp, start = (-110).dp)
                .size(250.dp)
                .clip(CircleShape)
                .background(Color(0x222A67FF))
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 22.dp, vertical = 14.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("N O U R", color = Color(0xFFB9F4FF), fontSize = 13.sp, fontWeight = FontWeight.Bold)
                    Text("OS  ·  CONCEPT 01", color = Color(0xFF8E9BB5), fontSize = 10.sp, letterSpacing = 1.4.sp)
                }
                Box(
                    modifier = Modifier
                        .clip(CircleShape)
                        .border(1.dp, Color(0x557FEAFF), CircleShape)
                        .background(Color(0x2222D3EE), CircleShape)
                        .padding(horizontal = 13.dp, vertical = 8.dp)
                ) {
                    Text("●  SYSTEM READY", color = Color(0xFFB9F4FF), fontSize = 9.sp, letterSpacing = 1.sp)
                }
            }

            Spacer(Modifier.height(30.dp))

            Text(time, color = Color.White, fontSize = 66.sp, lineHeight = 70.sp, fontWeight = FontWeight.Light, letterSpacing = (-2).sp)
            Text(date, color = Color(0xFFAEBAD0), fontSize = 14.sp)

            Spacer(Modifier.height(24.dp))

            GlassPanel(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(17.dp)) {
                    Text("YOUR SPACE", color = Color(0xFF94A8C8), fontSize = 10.sp, letterSpacing = 2.sp)
                    Spacer(Modifier.height(7.dp))
                    Text(
                        if (showAllApps) "All applications" else "Everything in its place.",
                        color = Color(0xFFF3F8FF),
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Medium
                    )
                    Spacer(Modifier.height(5.dp))
                    Text(
                        if (showAllApps) "Search your apps and open one with a tap." else "A calmer way to move through your day.",
                        color = Color(0xFFAAB8D0),
                        fontSize = 12.sp
                    )
                }
            }

            Spacer(Modifier.height(18.dp))

            OutlinedTextField(
                value = search,
                onValueChange = { search = it },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                shape = RoundedCornerShape(18.dp),
                placeholder = { Text("Search apps", color = Color(0xFF8D9AB2)) },
                leadingIcon = { Text("⌕", color = Color(0xFFB9F4FF), fontSize = 27.sp) },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                    focusedBorderColor = Color(0x887BEAFF),
                    unfocusedBorderColor = Color(0x334B6585),
                    focusedContainerColor = Color(0x33182438),
                    unfocusedContainerColor = Color(0x22182438),
                    cursorColor = Color(0xFFB9F4FF)
                )
            )

            Spacer(Modifier.height(16.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(if (showAllApps) "ALL APPS" else "QUICK LAUNCH", color = Color(0xFF9BAEC9), fontSize = 10.sp, letterSpacing = 2.sp)
                Text(
                    if (showAllApps) "HOME" else "VIEW ALL  ↗",
                    color = Color(0xFFB9F4FF),
                    fontSize = 10.sp,
                    modifier = Modifier
                        .clip(RoundedCornerShape(10.dp))
                        .clickable {
                            showAllApps = !showAllApps
                            search = ""
                        }
                        .padding(horizontal = 8.dp, vertical = 6.dp)
                )
            }

            Spacer(Modifier.height(8.dp))

            val filteredApps = apps.filter { it.name.contains(search, ignoreCase = true) }
            val visibleApps = if (showAllApps || search.isNotBlank()) filteredApps else filteredApps.take(8)

            AnimatedVisibility(
                visible = visibleApps.isNotEmpty(),
                enter = fadeIn() + scaleIn(initialScale = 0.98f),
                exit = fadeOut() + scaleOut(targetScale = 0.98f)
            ) {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(4),
                    modifier = Modifier.weight(1f),
                    contentPadding = PaddingValues(top = 8.dp, bottom = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    items(visibleApps, key = { it.packageName }) { app ->
                        AppTile(app = app) {
                            val launch = context.packageManager.getLaunchIntentForPackage(app.packageName)
                            if (launch != null) {
                                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                context.startActivity(launch)
                            }
                        }
                    }
                }
            }

            if (visibleApps.isEmpty()) {
                Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                    Text("No matching apps", color = Color(0xFF9BAEC9), fontSize = 13.sp)
                }
            }

            GlassPanel(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    DockItem("⌂", "HOME", selected = !showAllApps) { showAllApps = false; search = "" }
                    DockItem("▦", "APPS", selected = showAllApps) { showAllApps = true; search = "" }
                    DockItem("◌", "NOUR", selected = false) {
                        showAllApps = false
                        search = ""
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun AppTile(app: NourApp, onClick: () -> Unit) {
    var pressed by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(if (pressed) 0.94f else 1f, label = "tileScale")
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .scale(scale)
            .clip(RoundedCornerShape(18.dp))
            .clickable {
                pressed = true
                onClick()
                pressed = false
            }
            .padding(vertical = 5.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Image(
            bitmap = remember(app.packageName) { app.icon.toNourBitmap().asImageBitmap() },
            contentDescription = app.name,
            modifier = Modifier
                .size(48.dp)
                .clip(RoundedCornerShape(15.dp))
        )
        Spacer(Modifier.height(7.dp))
        Text(
            text = app.name,
            color = Color(0xFFE6EDF9),
            fontSize = 10.sp,
            textAlign = TextAlign.Center,
            maxLines = 1
        )
    }
}

@Composable
private fun DockItem(symbol: String, label: String, selected: Boolean, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(13.dp))
            .clickable(onClick = onClick)
            .background(if (selected) Color(0x3328CDE7) else Color.Transparent)
            .padding(horizontal = 17.dp, vertical = 5.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(symbol, color = if (selected) Color(0xFFB9F4FF) else Color(0xFF9BAEC9), fontSize = 20.sp)
        Text(label, color = if (selected) Color(0xFFB9F4FF) else Color(0xFF9BAEC9), fontSize = 8.sp, letterSpacing = 1.sp)
    }
}

@Composable
private fun GlassPanel(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(24.dp))
            .background(
                Brush.linearGradient(
                    listOf(Color(0x553B5578), Color(0x221B2A42), Color(0x332A3151))
                )
            )
            .border(1.dp, Color(0x4479DDF4), RoundedCornerShape(24.dp))
    ) {
        content()
    }
}

private fun loadLaunchableApps(context: Context): List<NourApp> {
    val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
    return context.packageManager.queryIntentActivities(intent, PackageManager.MATCH_ALL)
        .mapNotNull { resolve ->
            val packageName = resolve.activityInfo?.packageName ?: return@mapNotNull null
            if (packageName == context.packageName) return@mapNotNull null
            NourApp(
                name = resolve.loadLabel(context.packageManager).toString(),
                packageName = packageName,
                icon = resolve.loadIcon(context.packageManager)
            )
        }
        .distinctBy { it.packageName }
        .sortedBy { it.name.lowercase(Locale.getDefault()) }
}

private fun Drawable.toNourBitmap(): Bitmap {
    val width = intrinsicWidth.coerceAtLeast(1).coerceAtMost(192)
    val height = intrinsicHeight.coerceAtLeast(1).coerceAtMost(192)
    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    setBounds(0, 0, canvas.width, canvas.height)
    draw(canvas)
    return bitmap
}
