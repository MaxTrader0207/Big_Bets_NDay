from pathlib import Path
import re

path = Path(__file__).resolve().parents[1] / "index.html"
text = path.read_text(encoding="utf-8")
text = text.replace("Yahoo Finance 延遲行情｜每 15 秒更新", "Yahoo Finance 延遲行情｜GitHub Actions 約每 15 分鐘更新")
text = text.replace("const RADAR_INTERVAL=15000;", "const RADAR_INTERVAL=0;\nlet staticData=null,staticRadar=null;")

old_load = re.compile(r"async function loadFubonData\(date,broker=currentBroker,silent=false\).*?\nfunction groupFor", re.S)
new_load = """async function loadStaticFiles(){if(staticData&&staticRadar)return;const [a,b]=await Promise.all([fetch('data/latest.json',{cache:'no-store'}),fetch('data/radar.json',{cache:'no-store'})]);if(!a.ok||!b.ok)throw new Error('GitHub 靜態資料不存在');staticData=await a.json();staticRadar=await b.json()}\nasync function loadFubonData(date,broker=currentBroker,silent=false){try{await loadStaticFiles();if(staticData.date!==date){if(!silent)document.getElementById('sourceStatus').textContent='● GitHub 資料日期為 '+staticData.date;return []}const data=staticData.branches?.[broker]||[];if(!data.length&&!silent)document.getElementById('sourceStatus').textContent='● 該分點本次無可用資料';else if(!silent)document.getElementById('sourceStatus').textContent='● GitHub 靜態資料｜更新 '+new Date(staticData.updatedAt).toLocaleString('zh-TW');return data}catch(e){if(!silent)document.getElementById('sourceStatus').textContent='● GitHub 資料讀取失敗';return []}}\nfunction groupFor"""
text, n = old_load.subn(new_load, text, count=1)
if n != 1:
    raise SystemExit('loadFubonData replacement failed')

old_quote = re.compile(r"async function fetchYahooQuote\(item\).*?\nasync function refreshRadar", re.S)
new_quote = """async function fetchYahooQuote(item){try{await loadStaticFiles();const q=staticRadar?.quotes?.[item.code];if(!q)return {error:true,errorReason:'尚未納入最近一次 GitHub 更新'};if(q.error)return {error:true,errorReason:'GitHub 更新時讀取失敗'};return {price:q.price,change:q.change,changePct:q.changePct,volume:q.volume,name:q.name,time:q.updatedAt?new Date(q.updatedAt).toLocaleTimeString('zh-TW',{hour12:false}):'已更新'}}catch(e){return {error:true,errorReason:'GitHub 靜態資料不存在'}}}\nasync function refreshRadar"""
text, n = old_quote.subn(new_quote, text, count=1)
if n != 1:
    raise SystemExit('fetchYahooQuote replacement failed')

text = text.replace("document.getElementById('radarStatus').textContent='Yahoo 延遲行情更新中…';", "document.getElementById('radarStatus').textContent='讀取 GitHub 靜態行情資料…';")
text = text.replace("'Yahoo 延遲行情讀取失敗｜'+(reasons.join('、')||'請檢查網路或 API')", "'GitHub 靜態行情讀取失敗｜'+(reasons.join('、')||'請先執行 Actions 更新')")
text = text.replace("`Yahoo 延遲行情部分失敗｜${failed} 檔無資料｜${now}`", "`GitHub 靜態行情部分失敗｜${failed} 檔無資料｜${now}`")
text = text.replace("'Yahoo 延遲行情｜最後更新 '+now", "'GitHub 靜態行情｜最後更新 '+now")
text = text.replace("refreshRadar();radarTimer=setInterval(refreshRadar,RADAR_INTERVAL)", "refreshRadar()")
path.write_text(text, encoding="utf-8")
