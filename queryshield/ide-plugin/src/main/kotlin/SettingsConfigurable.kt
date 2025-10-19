package io.queryshield

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.project.Project
import javax.swing.JCheckBox
import javax.swing.JComponent
import javax.swing.JPanel
import javax.swing.JTextField

class SettingsConfigurable(private val project: Project) : Configurable {
  private var panel: JPanel? = null
  private lateinit var pythonField: JTextField
  private lateinit var budgetsField: JTextField
  private lateinit var explainCheck: JCheckBox

  override fun getDisplayName(): String = "QueryShield"

  override fun createComponent(): JComponent {
    val p = JPanel()
    p.layout = java.awt.GridLayout(0, 2)
    p.add(javax.swing.JLabel("Python path"))
    pythonField = JTextField()
    p.add(pythonField)
    p.add(javax.swing.JLabel("Budgets file"))
    budgetsField = JTextField()
    p.add(budgetsField)
    p.add(javax.swing.JLabel("Run with EXPLAIN"))
    explainCheck = JCheckBox()
    p.add(explainCheck)
    panel = p
    reset()
    return p
  }

  override fun isModified(): Boolean {
    val st = Settings.getInstance(project).state
    return (pythonField.text != (st.pythonPath ?: "")) ||
           (budgetsField.text != (st.budgetsPath ?: "")) ||
           (explainCheck.isSelected != st.runExplain)
  }

  override fun apply() {
    val s = Settings.getInstance(project)
    val st = s.state
    st.pythonPath = pythonField.text.ifBlank { null }
    st.budgetsPath = budgetsField.text.ifBlank { null }
    st.runExplain = explainCheck.isSelected
  }

  override fun reset() {
    val st = Settings.getInstance(project).state
    pythonField.text = st.pythonPath ?: ""
    val current = st.budgetsPath ?: ""
    if (current.isNotBlank()) {
      budgetsField.text = current
    } else {
      val base = project.basePath
      val candidate = if (base != null) java.io.File(base, "queryshield.yml") else null
      budgetsField.text = if (candidate != null && candidate.exists()) candidate.absolutePath else "queryshield.yml"
    }
    explainCheck.isSelected = st.runExplain
  }
}
