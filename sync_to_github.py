import os
import re
import time
import json
import subprocess
import requests
from bs4 import BeautifulSoup

# ==================== カスタマイズ設定 ====================
WRITENING_URL = "https://writening.net/page?XwwNSm"
INTERVAL_SECONDS = 30  # 巡回チェックの間隔（秒）

# 【超重要】GitHub Pagesの公開URL( game/nazonazo )と完全に一致する正しいパスを指定
HTML_FILE_PATH = "nazonazo/index.html"
# =========================================================

def fetch_and_parse_riddles():
    """Writeningから最新データをダウンロードして解析する"""
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔍 Writening.netを巡回チェック中...")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(WRITENING_URL, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        content_element = soup.find(class_="section-item")
        
        if not content_element:
            print("[警告] 本文エリア(section-item)が見つかりませんでした。")
            return None
            
        raw_text = content_element.get_text(strip=True)
        matches = re.findall(r'\{(.*?)\}', raw_text)
        
        parsed_list = []
        for match in matches:
            parts = match.split('|')
            if len(parts) >= 2:
                parsed_list.append({
                    "question": parts[0],
                    "answer": parts[1],
                    "explanation": parts[2] if len(parts) > 2 else ""
                })
        return parsed_list
    except Exception as e:
        print(f"[通信エラー] データの取得に失敗しました: {e}")
        return None

def update_html_file(riddles_data):
    """正しい位置にあるHTMLファイル(nazonazo/index.html)の中身を安全に書き換える"""
    if not os.path.exists(HTML_FILE_PATH):
        print(f"[致命的エラー] ターゲットファイルが見つかりません: {HTML_FILE_PATH}")
        print("フォルダの作成に失敗しているか、配置が違います。")
        return False
            
    with open(HTML_FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    riddles_json = json.dumps(riddles_data, ensure_ascii=False)
    
    # HTML内の let riddles = [...]; を最新データに置換する正規表現
    pattern = r'let riddles\s*=\s*\[.*?\]\s*;'
    replacement = f'let riddles = {riddles_json};'
    
    if not re.search(pattern, content):
        pattern = r'let riddles\s*=\s*\[\s*\]'
        
    new_content = re.sub(pattern, replacement, content)
    
    # 内容に変化がない場合は書き換えない（無駄なGitプッシュを防止）
    if content == new_content:
        return False
        
    with open(HTML_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[データ更新完了] 『{HTML_FILE_PATH}』に {len(riddles_data)} 問のデータを正常注入しました。")
    return True

def push_to_github():
    """新しく作ったフォルダ構造ごとGitHubへ完全にコミット＆プッシュする"""
    print("[GitHub送信] 変更を検知しました。GitHubサーバーへ自動アップロード中...")
    try:
        # 新しいフォルダ（nazonazo）や変更されたファイルを全てGitの追跡対象に加える
        subprocess.run(["git", "add", "."], check=True)
        
        # 自動コミット
        commit_msg = f"Fix folder layout & Auto-sync riddles: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        # 現在使用中のブランチ名（mainかmaster）を自動検出
        br_res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
        current_branch = br_res.stdout.strip()
        
        # GitHubの同じブランチへアップロードを実行
        subprocess.run(["git", "push", "origin", current_branch], check=True)
        print("🎉 【アップロード成功】GitHubへのファイル転送が100%完了しました！")
        print("💡 案内: GitHub Pages側で公開サイトが再構築されるまで、1〜3分ほどお待ちください。")
    except subprocess.CalledProcessError as e:
        print(f"[Gitエラー] 送信処理中に何らかのエラーが発生しました: {e}")

if __name__ == "__main__":
    print("==================================================")
    print("🚀 【新・フォルダ完全一致版】自動同期システム起動")
    print(f"   同期ファイル: {HTML_FILE_PATH}")
    print(f"   チェック間隔: {INTERVAL_SECONDS}秒ごと")
    print("==================================================")
    
    try:
        while True:
            riddles = fetch_and_parse_riddles()
            if riddles:
                is_changed = update_html_file(riddles)
                if is_changed:
                    push_to_github()
                else:
                    print("[スキップ] Writeningに変更がないため、送信をパスしました。")
                    
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[停止] システムを安全に終了しました。")
