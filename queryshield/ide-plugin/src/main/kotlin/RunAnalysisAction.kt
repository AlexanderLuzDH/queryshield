package io.queryshield

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.OSProcessHandler
import com.intellij.execution.ui.ConsoleView
import com.intellij.execution.ui.ConsoleViewContentType
import com.intellij.execution.ui.ConsoleViewImpl
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindowManager
import com.intellij.ui.content.ContentFactory

class RunAnalysisAction : AnAction("Analyze with QueryShield") {
  override fun actionPerformed(e: AnActionEvent) {
    val project = e.project ?: return
    val settings = Settings.getInstance(project).state
    // Prefer project SDK if available (Python plugin)
    var python = settings.pythonPath ?: "python"
    try {
      val sdk = com.jetbrains.python.sdk.PythonSdkUtil.findPythonSdk(project)
      val exe = sdk?.homePath
      if (exe != null) python = exe
    } catch (_: Throwable) {}
    val budgets = settings.budgetsPath ?: "queryshield.yml"
    val explainFlag = if ((settings.runExplain)) "--explain" else "--no-explain"
    val cmd = GeneralCommandLine(python, "-m", "queryshield_cli", "analyze", explainFlag, "--runner=django", "--budgets=${budgets}")
      .withWorkDirectory(project.basePath)
      .withEnvironment(System.getenv())
    val handler = OSProcessHandler(cmd)
    val console: ConsoleView = ConsoleViewImpl(project, true)
    console.attachToProcess(handler)

    val toolWindow = ToolWindowManager.getInstance(project).getToolWindow("QueryShield")
    if (toolWindow != null) {
      val content = ContentFactory.getInstance().createContent(console.component, "Run", false)
      toolWindow.contentManager.addContent(content)
      toolWindow.activate(null)
    } else {
      console.print("QueryShield: Run console initialized\n", ConsoleViewContentType.SYSTEM_OUTPUT)
    }
    handler.startNotify()
  }
}
