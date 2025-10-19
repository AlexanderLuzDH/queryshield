"""GitHub Checks API integration for QueryShield"""

import * as github from '@actions/github';
import * as core from '@actions/core';
import { exec } from '@actions/exec';
import { readFileSync } from 'fs';

interface CheckConclusion {
  conclusion: 'success' | 'failure' | 'neutral' | 'cancelled';
  title: string;
  summary: string;
  text: string;
}

interface QueryShieldReport {
  test_name: string;
  queries_total: number;
  queries_budget?: number;
  duration_ms: number;
  duration_budget_ms?: number;
  problems: Array<{
    type: string;
    sql: string;
    count?: number;
  }>;
  budget_violations: Array<{
    test: string;
    type: string;
    actual: number;
    max: number;
  }>;
}

export class GitHubChecksReporter {
  private octokit: ReturnType<typeof github.getOctokit>;
  private context = github.context;

  constructor(token: string) {
    this.octokit = github.getOctokit(token);
  }

  async createCheck(
    name: string,
    headSha: string,
    status: 'queued' | 'in_progress' | 'completed' = 'in_progress'
  ): Promise<number> {
    const response = await this.octokit.rest.checks.create({
      owner: this.context.repo.owner,
      repo: this.context.repo.repo,
      name,
      head_sha: headSha,
      status,
    });

    return response.data.id;
  }

  async completeCheck(
    checkId: number,
    headSha: string,
    conclusion: CheckConclusion
  ): Promise<void> {
    await this.octokit.rest.checks.update({
      owner: this.context.repo.owner,
      repo: this.context.repo.repo,
      check_run_id: checkId,
      status: 'completed',
      conclusion: conclusion.conclusion,
      output: {
        title: conclusion.title,
        summary: conclusion.summary,
        text: conclusion.text,
        annotations: this.generateAnnotations(conclusion),
      },
    });
  }

  private generateAnnotations(
    conclusion: CheckConclusion
  ): Array<{
    path: string;
    start_line: number;
    end_line: number;
    annotation_level: 'notice' | 'warning' | 'failure';
    message: string;
  }> {
    // Annotations would be generated from test file locations
    // For now, return empty array (could be enhanced with file detection)
    return [];
  }

  async reportQueryShieldAnalysis(
    report: QueryShieldReport,
    baselineReport?: QueryShieldReport
  ): Promise<void> {
    const headSha = this.context.sha;
    const checkId = await this.createCheck(
      'QueryShield Performance Analysis',
      headSha,
      'in_progress'
    );

    try {
      const conclusion = this.analyzeReport(report, baselineReport);
      await this.completeCheck(checkId, headSha, conclusion);
    } catch (error) {
      await this.completeCheck(checkId, headSha, {
        conclusion: 'failure',
        title: 'QueryShield Analysis Failed',
        summary: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        text: `Failed to complete QueryShield analysis`,
      });
      throw error;
    }
  }

  private analyzeReport(
    report: QueryShieldReport,
    baseline?: QueryShieldReport
  ): CheckConclusion {
    const budgetViolations = report.budget_violations || [];
    const hasViolations = budgetViolations.length > 0;

    let conclusion: CheckConclusion = {
      conclusion: hasViolations ? 'failure' : 'success',
      title: hasViolations
        ? `❌ ${budgetViolations.length} Budget Violation(s)`
        : '✅ All Budgets Met',
      summary: this.generateSummary(report, baseline),
      text: this.generateDetailedReport(report, baseline),
    };

    return conclusion;
  }

  private generateSummary(
    report: QueryShieldReport,
    baseline?: QueryShieldReport
  ): string {
    const queries = report.queries_total;
    const budget = report.queries_budget || 'N/A';
    const duration = report.duration_ms;
    const durationBudget = report.duration_budget_ms || 'N/A';

    let summary = `## QueryShield Analysis Results\n\n`;
    summary += `### Query Performance\n`;
    summary += `- **Total Queries:** ${queries}${
      budget !== 'N/A' ? ` (budget: ${budget})` : ''
    }\n`;
    summary += `- **Total Duration:** ${duration}ms${
      durationBudget !== 'N/A' ? ` (budget: ${durationBudget}ms)` : ''
    }\n`;

    if (baseline) {
      const queryDelta = queries - baseline.queries_total;
      const durationDelta = duration - baseline.duration_ms;
      const queryPercent = ((queryDelta / baseline.queries_total) * 100).toFixed(
        1
      );
      const durationPercent = (
        (durationDelta / baseline.duration_ms) *
        100
      ).toFixed(1);

      summary += `\n### vs. Baseline\n`;
      summary += `- **Queries:** ${queryDelta > 0 ? '+' : ''}${queryDelta} (${queryPercent}%)\n`;
      summary += `- **Duration:** ${durationDelta > 0 ? '+' : ''}${durationDelta}ms (${durationPercent}%)\n`;
    }

    if (report.problems && report.problems.length > 0) {
      summary += `\n### Problems Detected\n`;
      const problemTypes = new Map<string, number>();
      report.problems.forEach((p) => {
        problemTypes.set(p.type, (problemTypes.get(p.type) || 0) + 1);
      });

      problemTypes.forEach((count, type) => {
        summary += `- **${type}:** ${count}\n`;
      });
    }

    return summary;
  }

  private generateDetailedReport(
    report: QueryShieldReport,
    baseline?: QueryShieldReport
  ): string {
    let text = `## Detailed Analysis\n\n`;

    // Budget violations
    if (report.budget_violations && report.budget_violations.length > 0) {
      text += `### 🔴 Budget Violations\n\n`;
      report.budget_violations.forEach((violation) => {
        const overage = (
          ((violation.actual / violation.max) * 100 - 100)
        ).toFixed(0);
        text += `- **${violation.test}** (${violation.type}): ${violation.actual} / ${violation.max} (+${overage}%)\n`;
      });
      text += '\n';
    }

    // Problems
    if (report.problems && report.problems.length > 0) {
      text += `### ⚠️ Performance Problems\n\n`;
      const grouped = new Map<string, typeof report.problems>();

      report.problems.forEach((p) => {
        if (!grouped.has(p.type)) {
          grouped.set(p.type, []);
        }
        grouped.get(p.type)!.push(p);
      });

      grouped.forEach((problems, type) => {
        text += `**${type}** (${problems.length} occurrences)\n`;
        problems.slice(0, 3).forEach((p) => {
          text += `- \`${p.sql.substring(0, 80)}\`${p.count ? ` (${p.count}x)` : ''}\n`;
        });
        if (problems.length > 3) {
          text += `- ... and ${problems.length - 3} more\n`;
        }
        text += '\n';
      });
    }

    // Recommendations
    text += `### 💡 Recommendations\n\n`;
    text += `1. Review budget violations in the [QueryShield Dashboard](https://app.queryshield.io)\n`;
    text += `2. Check [N+1 patterns](https://docs.queryshield.io/n-plus-one) in detected problems\n`;
    text += `3. Use [optimization guide](https://docs.queryshield.io/optimization) for fixes\n`;

    return text;
  }
}

// Main action entry point
export async function run(): Promise<void> {
  try {
    const token = core.getInput('github-token') || process.env.GITHUB_TOKEN || '';
    const apiKey = core.getInput('api-key');
    const reportPath = core.getInput('report-path') || '.queryshield/report.json';

    const reporter = new GitHubChecksReporter(token);

    // Read report
    let report: QueryShieldReport;
    try {
      const reportContent = readFileSync(reportPath, 'utf-8');
      report = JSON.parse(reportContent);
    } catch (error) {
      core.setFailed(`Failed to read report: ${reportPath}`);
      return;
    }

    // Optional: fetch baseline
    let baseline: QueryShieldReport | undefined;
    if (apiKey) {
      try {
        // Fetch baseline from SaaS
        const response = await fetch(
          'https://api.queryshield.app/api/baseline',
          {
            headers: {
              Authorization: `Bearer ${apiKey}`,
            },
          }
        );
        if (response.ok) {
          baseline = await response.json();
        }
      } catch (error) {
        core.warning(`Failed to fetch baseline: ${error}`);
      }
    }

    // Report analysis
    await reporter.reportQueryShieldAnalysis(report, baseline);

    // Set outputs
    core.setOutput('violations-count', report.budget_violations?.length || 0);
    core.setOutput(
      'problems-count',
      report.problems?.length || 0
    );

    if (report.budget_violations && report.budget_violations.length > 0) {
      core.setFailed(
        `${report.budget_violations.length} budget violation(s) detected`
      );
    }
  } catch (error) {
    core.setFailed(error instanceof Error ? error.message : String(error));
  }
}

// Run if executed directly
if (require.main === module) {
  run();
}
