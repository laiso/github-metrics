import os
import sys
import json
import csv
import subprocess
import argparse
import requests
import shutil
from datetime import datetime



class GitHubClient:
    def __init__(self):
        self.token = self._get_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _get_token(self):
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            return token.strip()
        if shutil.which("gh"):
            try:
                result = subprocess.run(
                    ["gh", "auth", "token"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout.strip()
            except subprocess.CalledProcessError:
                pass
        print("Error: No GitHub token found. Set GITHUB_TOKEN or use 'gh auth login'.")
        sys.exit(1)

    def run_query(self, query, variables=None):
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables or {}},
            headers=self.headers
        )
        if response.status_code != 200:
            raise Exception(f"API Error {response.status_code}: {response.text}")
        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL Error: {data['errors']}")
        return data



def get_viewer_info(client):
    query = """
    query { viewer { login id } }
    """
    data = client.run_query(query)
    return data['data']['viewer']

def fetch_repo_stats(client, viewer_id, years):
    commit_counts = {year: 0 for year in years}
    
    # Construct query parts dynamically
    history_fields = ""
    for year in years:
        start = f"{year}-01-01T00:00:00Z"
        end = f"{year}-12-31T23:59:59Z"
        history_fields += f"""
        h{year}: history(since: "{start}", until: "{end}", author: {{id: "{viewer_id}"}}) {{ totalCount }}
        """

    query = f"""
    query($cursor: String) {{
        viewer {{
            repositories(first: 50, after: $cursor, ownerAffiliations: [OWNER]) {{
                pageInfo {{ hasNextPage endCursor }}
                nodes {{
                    name
                    defaultBranchRef {{
                        target {{
                            ... on Commit {{ {history_fields} }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    """
    
    cursor = None
    has_next = True
    total_repos = 0
    
    while has_next:
        data = client.run_query(query, {"cursor": cursor})
        repos = data['data']['viewer']['repositories']
        
        for repo in repos['nodes']:
            if repo.get('defaultBranchRef') and repo['defaultBranchRef'].get('target'):
                target = repo['defaultBranchRef']['target']
                for year in years:
                    key = f"h{year}"
                    if key in target:
                        commit_counts[year] += target[key]['totalCount']
        
        batch_count = len(repos['nodes'])
        total_repos += batch_count
        
        has_next = repos['pageInfo']['hasNextPage']
        cursor = repos['pageInfo']['endCursor']
        
    return commit_counts

def fetch_search_metrics(client, username, year):
    query = """
    query($q_prs: String!, $q_merged: String!, $q_issues: String!) {
        prs: search(query: $q_prs, type: ISSUE) { issueCount }
        merged: search(query: $q_merged, type: ISSUE) { issueCount }
        issues: search(query: $q_issues, type: ISSUE) { issueCount }
    }
    """
    variables = {
        "q_prs": f"is:pr author:{username} created:{year}-01-01..{year}-12-31",
        "q_merged": f"is:pr is:merged author:{username} merged:{year}-01-01..{year}-12-31",
        "q_issues": f"is:issue author:{username} created:{year}-01-01..{year}-12-31"
    }
    data = client.run_query(query, variables)
    return {
        "prs_created": data['data']['prs']['issueCount'],
        "prs_merged": data['data']['merged']['issueCount'],
        "issues_created": data['data']['issues']['issueCount']
    }



def main():
    current_year = datetime.now().year
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, nargs="+", default=[current_year - 1, current_year], help="Years to analyze")
    args = parser.parse_args()
    years = sorted(list(set(args.year)))

    try:
        client = GitHubClient()
        viewer = get_viewer_info(client)
        print(f"Authenticated as: {viewer['login']} (ID: {viewer['id']})")
        
        # 1. Commits (Strict Scan)
        commit_counts = fetch_repo_stats(client, viewer['id'], years)
        
        # 2. Search Metrics (PRs/Issues)
        results = []
        for year in years:
            metrics = fetch_search_metrics(client, viewer['login'], year)
            results.append({
                "year": year,
                "commits": commit_counts.get(year, 0),
                "prs_created": metrics['prs_created'],
                "prs_merged": metrics['prs_merged'],
                "issues_created": metrics['issues_created']
            })
            
        # 3. Output
        print("\n=== GitHub Metrics Report ===")
        print(f"| {'Year':<6} | {'Commits':<10} | {'PRs Created':<12} | {'PRs Merged':<12} | {'Issues':<8} |")
        print(f"|{'-'*8}|{'-'*12}|{'-'*14}|{'-'*14}|{'-'*10}|")
        
        for r in results:
            print(f"| {r['year']:<6} | {r['commits']:<10} | {r['prs_created']:<12} | {r['prs_merged']:<12} | {r['issues_created']:<8} |")
            
        # Save files
        output_dir = "out"
        os.makedirs(output_dir, exist_ok=True)
            
        with open(os.path.join(output_dir, "metrics_report.json"), "w") as f:
            json.dump(results, f, indent=2)
            
        with open(os.path.join(output_dir, "metrics_report.csv"), "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Year", "Commits", "PRs Created", "PRs Merged", "Issues Created"])
            for r in results:
                writer.writerow([r['year'], r['commits'], r['prs_created'], r['prs_merged'], r['issues_created']])
                
        print(f"\nSaved to {output_dir}/metrics_report.json and {output_dir}/metrics_report.csv")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
