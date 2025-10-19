import * as core from '@actions/core';
import * as github from '@actions/github';
import * as exec from '@actions/exec';
import * as fs from 'fs';
import * as path from 'path';

interface Report {
  tests: Array<{
    name: string;
    queries_total: number;
    duration_ms: number;
    problems: Array<{ type: string; id: string }>;
  }>;
  cost_analysis?: {
    estimated_monthly_cost: number;
    total_queries: number;
  };
}

async function run() {
  try {
    const budgetsFile = core.getInput('budgets-file');
    const compareTo = core.getInput('compare-to');
    const runner = core.getInput('runner');
    const explain = core.getInput('explain') === 'true';
    const apiKey = core.getInput('api-key');
    const failOnViolations = core.getInput('fail-on-violations') === 'true';

    core.info('QueryShield: Analyzing database queries...');

    // Run QueryShield analyze command
    const reportPath = '.queryshield/current.json';
    const analyzeCmd = [
      'queryshield',
      'analyze',
      '--runner',
      runner,
      '--budgets',
      budgetsFile,
      '--output',
      reportPath,
      explain ? '--explain' : '--no-explain',
    ];

    await exec.exec('pip', ['install', 'queryshield', 'queryshield-probe']);
    await exec.exec('queryshield', analyzeCmd.slice(1));

    // Read current report
    const currentReport: Report = JSON.parse(
      fs.readFileSync(reportPath, 'utf-8')
    );

    // Try to fetch baseline from main branch
    let baselineReport: Report | null = null;
    try {
      await exec.exec('git', [
        'show',
        `${compareTo}:.queryshield/queryshield_report.json`,
      ]);
      const baselineContent = await exec.getExecOutput('git', [
        'show',
        `${compareTo}:.queryshield/queryshield_report.json`,
      ]);
      if (baselineContent.stdout) {
        baselineReport = JSON.parse(baselineContent.stdout);
      }
    } catch (e) {
      core.info('No baseline report found on ' + compareTo);
    }

    // Check budgets
    let violations: string[] = [];
    try {
      await exec.exec('queryshield', ['budget-check', '--budgets', budgetsFile, '--report', reportPath]);
    } catch (e) {
      // Extract violations from stderr
      violations.push('Budget violations detected');
    }

    // Generate PR comment
    let commentBody = '## 📊 QueryShield Analysis\n\n';

    // Summary table
    commentBody += '| Test | Queries | p95 (ms) | Problems | Cost |\n';
    commentBody += '|------|---------|---------|----------|------|\n';

    for (const test of currentReport.tests) {
      const problemTypes = [...new Set(test.problems.map((p) => p.type))].join(', ') || 'None';
      const cost = currentReport.cost_analysis?.estimated_monthly_cost || 'N/A';
      commentBody += `| ${test.name} | ${test.queries_total} | ${(test.duration_ms / 1000).toFixed(2)} | ${problemTypes} | $${cost} |\n`;
    }

    // Compare to baseline if available
    if (baselineReport) {
      commentBody += '\n### 📈 Comparison to ' + compareTo + '\n\n';

      const currentTotalQueries = currentReport.tests.reduce((sum, t) => sum + t.queries_total, 0);
      const baselineTotalQueries = baselineReport.tests.reduce((sum, t) => sum + t.queries_total, 0);
      const queryDelta = currentTotalQueries - baselineTotalQueries;
      const deltaPercent = baselineTotalQueries > 0 ? ((queryDelta / baselineTotalQueries) * 100).toFixed(1) : 0;

      core.setOutput('queries-delta', queryDelta);

      if (queryDelta > 0) {
        commentBody += `⚠️ Query count increased by **${queryDelta}** (+${deltaPercent}%)\n`;
      } else if (queryDelta < 0) {
        commentBody += `✅ Query count improved by **${Math.abs(queryDelta)}** (-${Math.abs(Number(deltaPercent))}%)\n`;
      } else {
        commentBody += `✅ Query count unchanged\n`;
      }
    }

    // Show violations if any
    if (violations.length > 0) {
      commentBody += '\n### ⚠️ Budget Violations\n\n';
      for (const violation of violations) {
        commentBody += `- ${violation}\n`;
      }
      core.setOutput('violations-count', violations.length.toString());

      if (failOnViolations) {
        core.setFailed('QueryShield budget violations detected');
      }
    }

    // Submit to SaaS dashboard if API key provided
    if (apiKey) {
      core.info('Submitting report to QueryShield dashboard...');
      const submitCmd = [
        'queryshield',
        'analyze',
        '--runner',
        runner,
        '--budgets',
        budgetsFile,
        '--output',
        reportPath,
        '--api-key',
        apiKey,
      ];
      try {
        await exec.exec('queryshield', submitCmd.slice(1));
        commentBody += '\n📤 [View full report on QueryShield Dashboard](https://queryshield.app/reports)\n';
        core.setOutput('report-url', 'https://queryshield.app/reports');
      } catch (e) {
        core.warning('Failed to submit to QueryShield dashboard');
      }
    }

    // Post comment to PR
    if (github.context.issue.number) {
      const octokit = github.getOctokit(process.env.GITHUB_TOKEN || '');
      await octokit.rest.issues.createComment({
        owner: github.context.repo.owner,
        repo: github.context.repo.repo,
        issue_number: github.context.issue.number,
        body: commentBody,
      });
    }

    core.info('QueryShield analysis complete!');
  } catch (error) {
    core.setFailed(error instanceof Error ? error.message : String(error));
  }
}

run();
