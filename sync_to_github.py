import os
import re
import time
import json
import subprocess
import requests
from bs4 import BeautifulSoup

# ==================== システム設定項目 ====================
WRITENING_URL = "https://writening.net/page?XwwNSm"
INTERVAL_SECONDS = 30  # 巡回チェックの間隔（秒）

# 【超重要】先ほど作った、大正解のフォルダパスを正確に指定してロックします
HTML_FILE_PATH = "nazonazo/index.html"
# =========================================================

def fetch_and_parse_riddles():
    """Writeningから最新のクイズデータをダウンロードして解析する"""
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔍 Writening.netをパトロール中...")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(WRITENING_URL, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        content_element = soup.find(class_="section-item")
        
        if not content_element:
            print("[警告] Writeningの本文(section-item)が見つかりませんでした。")
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
    """大正解のパス(nazonazo/index.html)の中身を安全に書き換える"""
    if not os.path.exists(HTML_FILE_PATH):
        print(f"[致命的エラー] 指定されたパスにHTMLファイルが存在しません: {HTML_FILE_PATH}")
        return False
            
    with open(HTML_FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    riddles_json = json.dumps(riddles_data, ensure_ascii=False)
    
    # HTML内の let riddles = [...]; の部分を最新データに一発置換
    pattern = r'let riddles\s*=\s*\[.*?\]\s*;'
    replacement = f'let riddles = {riddles_json};'
    
    if not re.search(pattern, content):
        pattern = r'let riddles\s*=\s*\[\s*\]'
        
    new_content = re.sub(pattern, replacement, content)
    
    # 前回の内容と完全に一致＝変化がない場合は、無駄な処理を避けるためスキップ
    if content == new_content:
        return False
        
    with open(HTML_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[データ書込成功] 『{HTML_FILE_PATH}』に {len(riddles_data)} 問のなぞなぞを注入しました。")
    return True

def push_to_github():
    """新しいフォルダ構造ごと、GitHubへコミット＆プッシュ（送信）する"""
    print("[GitHub送信] 変更をキャッチしました。GitHubサーバーへ転送を開始します...")
    try:
        # 新しいフォルダ（nazonazo）とその中身すべてをGitの送信リストに加える
        subprocess.run(["git", "add", "."], check=True)
        
        # コミットメッセージの作成
        commit_msg = f"Deploy correct folder layout & Auto-sync: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        # 現在使用中の有効なブランチ名（mainかmaster）を自動判別
        br_res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
        current_branch = br_res.stdout.strip()
        
        # GitHubの指定ブランチへ一気にアップロード！
        subprocess.run(["git", "push", "origin", current_branch], check=True)
        print("🎉 【完全大成功】GitHubへのアップロードが完了しました！")
        print("💡 豆知識: GitHubのロボットが公開サイトを組み立て直すまで、1分〜3分ほど時間がかかります。")
    except subprocess.CalledProcessError as e:
        print(f"[Gitエラー] 転送中にエラーが発生しました。通信環境などを確認してください: {e}")

if __name__ == "__main__":
    print("==================================================")
    print("🚀 【フォルダ構造・完全一致版】自動同期システム起動")
    print(f"   ターゲットファイル: {HTML_FILE_PATH}")
    print(f"   パトロール間隔    : {INTERVAL_SECONDS}秒ごと")
    print("==================================================")
    
    try:
        while True:
            riddles = fetch_and_parse_riddles()
            if riddles:
                is_changed = update_html_file(riddles)
                if is_changed:
                    push_to_github()
                else:
                    print("[変更なし] Writeningに変化はありません。送信をパスしました。")
                    
            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[停止] システムを安全に終了しました。")
