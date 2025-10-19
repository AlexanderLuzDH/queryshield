package io.queryshield

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.components.JBScrollPane
import com.intellij.ui.table.JBTable
import org.jetbrains.annotations.NotNull
import java.io.File
import javax.swing.JPanel
import javax.swing.table.DefaultTableModel
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFileManager
import com.intellij.openapi.vfs.newvfs.BulkFileListener
import com.intellij.openapi.vfs.newvfs.events.VFileEvent
import com.intellij.openapi.fileEditor.OpenFileDescriptor
import com.intellij.openapi.fileEditor.FileEditorManager
import javax.swing.JButton
import java.awt.Toolkit
import java.awt.datatransfer.StringSelection

class ToolWindowFactory : ToolWindowFactory {
  override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
    val panel = JPanel()
    panel.layout = java.awt.BorderLayout()
    val tableModel = DefaultTableModel(arrayOf("Test", "DB", "p95 (ms)", "Problems"), 0)
    val table = JBTable(tableModel)
    table.setDefaultRenderer(Object::class.java, object : javax.swing.table.DefaultTableCellRenderer() {
      override fun getTableCellRendererComponent(tbl: javax.swing.JTable?, value: Any?, isSelected: Boolean, hasFocus: Boolean, row: Int, column: Int): java.awt.Component {
        val c = super.getTableCellRendererComponent(tbl, value, isSelected, hasFocus, row, column)
        if (column == 3) { // Problems column
          val v = (value?.toString() ?: "0").toIntOrNull() ?: 0
          text = if (v == 0) "0 (PASS)" else "$v (WARN)"
          foreground = if (v == 0) java.awt.Color(0, 128, 0) else java.awt.Color(184, 134, 11)
        } else {
          foreground = if (isSelected) foreground else java.awt.Color.BLACK
        }
        return c
      }
    })
    val scroll = JBScrollPane(table)
    panel.add(scroll, java.awt.BorderLayout.CENTER)

    // Problems table
    val problemsModel = DefaultTableModel(arrayOf("Test", "Type", "Top Frame", "ID"), 0)
    val problemsTable = JBTable(problemsModel)
    val problemsScroll = JBScrollPane(problemsTable)
    val bottom = JPanel()
    bottom.layout = java.awt.BorderLayout()
    bottom.add(problemsScroll, java.awt.BorderLayout.CENTER)
    val tools = JPanel()
    tools.layout = java.awt.FlowLayout(java.awt.FlowLayout.RIGHT)
    val openBtn = JButton("Open report")
    val filterBox = javax.swing.JComboBox(arrayOf("ALL", "N+1", "MISSING_INDEX", "SORT_WITHOUT_INDEX", "SELECT_STAR_LARGE"))
    val copyBtn = JButton("Copy fix")
    val rerun = JButton("Re-run analysis")
    rerun.addActionListener {
      io.queryshield.RunAnalysisAction().actionPerformed(
        com.intellij.openapi.actionSystem.AnActionEvent.createFromAnAction(
          io.queryshield.RunAnalysisAction(), null, "QueryShield", com.intellij.openapi.actionSystem.DataContext { null })
      )
      // Reload after a short delay
      javax.swing.Timer(1500) { loadReport() }.start()
    }
    openBtn.addActionListener {
      val chooser = javax.swing.JFileChooser(project.basePath)
      val res = chooser.showOpenDialog(panel)
      if (res == javax.swing.JFileChooser.APPROVE_OPTION) {
        System.setProperty("queryshield.report.path", chooser.selectedFile.absolutePath)
        loadReport()
      }
    }
    tools.add(openBtn)
    tools.add(javax.swing.JLabel("Filter:"))
    tools.add(filterBox)
    tools.add(copyBtn)
    tools.add(rerun)
    bottom.add(tools, java.awt.BorderLayout.EAST)
    panel.add(bottom, java.awt.BorderLayout.SOUTH)

    val content = com.intellij.ui.content.ContentFactory.getInstance().createContent(panel, "QueryShield", false)
    toolWindow.contentManager.addContent(content)

    fun openAt(path: String, line: Int) {
      val vf = LocalFileSystem.getInstance().findFileByPath(path)
      if (vf != null) {
        OpenFileDescriptor(project, vf, Math.max(0, line - 1), 0).navigate(true)
      }
    }

    val emptyLabel = javax.swing.JLabel("Run QueryShield to generate a report (Analyze with QueryShield)")
    emptyLabel.horizontalAlignment = javax.swing.SwingConstants.CENTER
    panel.add(emptyLabel, java.awt.BorderLayout.NORTH)

    var problemsIndex: MutableList<org.json.JSONObject> = mutableListOf()
    fun loadReport() {
      tableModel.rowCount = 0
      problemsModel.rowCount = 0
      problemsIndex.clear()
      val userPath = System.getProperty("queryshield.report.path")
      val f = if (userPath != null) File(userPath) else File(project.basePath ?: return, ".queryshield/queryshield_report.json")
      if (!f.exists()) return
      try {
        val text = f.readText()
        val json = org.json.JSONObject(text)
        val tests = json.optJSONArray("tests") ?: return
        emptyLabel.text = "QueryShield report: ${f.absolutePath}"
        for (i in 0 until tests.length()) {
          val t = tests.getJSONObject(i)
          val name = t.optString("name", "")
          val q = t.optInt("queries_total", 0)
          val p95 = t.optDouble("queries_p95_ms", 0.0)
          val parr = t.optJSONArray("problems")
          val probs = parr?.length() ?: 0
          var hasN1 = false
          if (parr != null) {
            for (k in 0 until parr.length()) {
              val typ = parr.getJSONObject(k).optString("type", "")
              if (typ == "N+1") { hasN1 = true; break }
            }
          }
          val statusVal = if (probs == 0) 0 else if (hasN1) -1 else probs
          tableModel.addRow(arrayOf(name, q, String.format("%.1f", p95), statusVal))
          val arr = t.optJSONArray("problems")
          if (arr != null) {
            for (j in 0 until arr.length()) {
              val p = arr.getJSONObject(j)
              val typ = p.optString("type", "")
              val id = p.optString("id", "")
              val ev = p.optJSONObject("evidence")
              val top = ev?.optJSONArray("top_stack")
              val topStr = if (top != null && top.length() >= 3) "${top.getString(0)}:${top.getInt(2)}" else ""
              val filter = filterBox.selectedItem?.toString() ?: "ALL"
              if (filter == "ALL" || filter == typ) {
                problemsIndex.add(p)
                problemsModel.addRow(arrayOf(name, typ, topStr, id))
              }
            }
          }
        }
      } catch (_: Exception) {}
    }

    problemsTable.addMouseListener(object : java.awt.event.MouseAdapter() {
      override fun mouseClicked(e: java.awt.event.MouseEvent) {
        if (e.clickCount == 2) {
          val row = problemsTable.selectedRow
          if (row >= 0) {
            val top = problemsModel.getValueAt(row, 2)?.toString() ?: return
            if (top.contains(":")) {
              val idx = top.lastIndexOf(":")
              val path = top.substring(0, idx)
              val line = top.substring(idx + 1).toIntOrNull() ?: 1
              openAt(path, line)
            }
          }
        }
      }
    })

    loadReport()
    filterBox.addActionListener { loadReport() }
    // Copy fix button
    copyBtn.addActionListener {
      val row = problemsTable.selectedRow
      if (row >= 0 && row < problemsIndex.size) {
        val pobj = problemsIndex[row]
        val sug = pobj.optJSONObject("suggestion")
        var text = ""
        if (sug != null) {
          val ddl = sug.optString("ddl", null)
          text = ddl ?: when (sug.optString("kind", "")) {
            "select_related" -> ".select_related()"
            "prefetch_related" -> ".prefetch_related()"
            "avoid_select_star" -> (sug.optJSONObject("args")?.optString("use") ?: ".only()")
            else -> sug.toString()
          }
        }
        if (text.isNotBlank()) {
          val sel = StringSelection(text)
          Toolkit.getDefaultToolkit().systemClipboard.setContents(sel, sel)
        }
      }
    }

    // Watch report for changes and debounce reload
    val conn = project.messageBus.connect()
    var timer: javax.swing.Timer? = null
    fun schedule() {
      if (timer != null) timer!!.stop()
      timer = javax.swing.Timer(500) { loadReport() }
      timer!!.isRepeats = false
      timer!!.start()
    }
    conn.subscribe(VirtualFileManager.VFS_CHANGES, object: BulkFileListener {
      override fun after(events: MutableList<out VFileEvent>) {
        val base = project.basePath ?: return
        val expected = (base + "/.queryshield/queryshield_report.json").replace('\\','/')
        for (e in events) {
          val p = e.path.replace('\\','/')
          if (p.endsWith("/.queryshield/queryshield_report.json") || p == expected) {
            schedule(); break
          }
        }
      }
    })
  }
}
