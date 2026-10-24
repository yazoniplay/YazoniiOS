package com.nour.os

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val NourColors = darkColorScheme(
    primary = Color(0xFFB8F4FF),
    onPrimary = Color(0xFF06212A),
    secondary = Color(0xFFB9B5FF),
    background = Color(0xFF070B15),
    surface = Color(0xFF111827),
    onBackground = Color(0xFFF4F7FF),
    onSurface = Color(0xFFF4F7FF)
)

@Composable
fun NourTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = NourColors,
        content = content
    )
}
