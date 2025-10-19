package io.queryshield

import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage

@State(name = "QueryShieldSettings", storages = [Storage("queryshield.xml")])
class Settings : PersistentStateComponent<Settings.State> {
    data class State(
        var pythonPath: String? = null,
        var budgetsPath: String? = "queryshield.yml",
        var runExplain: Boolean = true
    )

    private var myState = State()

    override fun getState(): State = myState
    override fun loadState(state: State) { myState = state }

    companion object {
        fun getInstance(project: com.intellij.openapi.project.Project): Settings {
            return project.getService(Settings::class.java)
        }
    }
}
