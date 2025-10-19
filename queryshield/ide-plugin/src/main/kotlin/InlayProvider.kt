package io.queryshield

import com.intellij.codeInsight.hints.InlayHintsCollector
import com.intellij.codeInsight.hints.InlayHintsProvider
import com.intellij.codeInsight.hints.InlayHintsSink
import com.intellij.codeInsight.hints.SettingsKey
import com.intellij.openapi.editor.Editor
import com.intellij.psi.PsiElement
import com.jetbrains.python.psi.PyFunction
import java.io.File

class InlayProvider : InlayHintsProvider<NoSettings> {
  override val key: SettingsKey<NoSettings> = SettingsKey("QueryShieldInlays")
  override val name: String = "QueryShield"
  override fun createConfigurable(settings: NoSettings) = null
  override fun getCollectorFor(file: com.intellij.psi.PsiFile, editor: Editor, settings: NoSettings, sink: InlayHintsSink): InlayHintsCollector? {
    val project = file.project
    val base = project.basePath ?: return null
    val reportFile = File(base, ".queryshield/queryshield_report.json")
    val data: Map<String, Triple<Int, Double, Int>> = try {
      if (!reportFile.exists()) return null
      val text = reportFile.readText()
      val json = org.json.JSONObject(text)
      val tests = json.getJSONArray("tests")
      val map = HashMap<String, Triple<Int, Double, Int>>()
      for (i in 0 until tests.length()) {
        val t = tests.getJSONObject(i)
        val name = t.getString("name")
        val q = t.optInt("queries_total", 0)
        val p95 = t.optDouble("queries_p95_ms", 0.0)
        val probs = t.optJSONArray("problems")?.length() ?: 0
        map[name] = Triple(q, p95, probs)
      }
      map
    } catch (_: Exception) { emptyMap() }

    return InlayHintsCollector { element: PsiElement, _: Editor, sink2: InlayHintsSink ->
      if (element is PyFunction) {
        val fn = element.name ?: return@InlayHintsCollector
        if (!fn.startsWith("test_")) return@InlayHintsCollector
        // naive match: end with function name
        val match = data.entries.find { it.key.endsWith(".$fn") }
        if (match != null) {
          val (q, p95, probs) = match.value
          val warn = if (probs > 0) " · \u26A0 $probs" else ""
          val text = "DB: $q · p95: ${String.format("%.1f", p95)}$warn"
          val factory = com.intellij.codeInsight.hints.presentation.PresentationFactory(editor)
          val pres = factory.smallText(text)
          sink2.addInlineElement(element.textOffset, false, pres, false)
        }
      }
    }
  }
  override fun createSettings(): NoSettings = NoSettings()
}

class NoSettings
