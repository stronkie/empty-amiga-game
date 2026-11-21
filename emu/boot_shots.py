import asyncio,json,sys,urllib.parse
from playwright.async_api import async_playwright
adf,out=sys.argv[1],sys.argv[2]
cfg={"url":f"http://127.0.0.1:8000/games/{adf}","AROS":True,"port2":True,"navbar":False,"dialog_on_missing_roms":False,"dialog_on_disk":False}
url="http://127.0.0.1:8000/index.html#"+json.dumps(cfg)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--autoplay-policy=no-user-gesture-required','--use-gl=swiftshader','--enable-unsafe-swiftshader'])
        pg=await b.new_page(viewport={'width':1024,'height':800})
        logs=[]; pg.on('console',lambda m: logs.append(m.text)); pg.on('pageerror',lambda e: logs.append('ERR '+str(e)))
        await pg.goto(url); 
        shots=[int(x) for x in sys.argv[3].split(',')]
        t=0
        for i,s in enumerate(shots):
            await pg.wait_for_timeout((s-t)*1000); t=s
            await pg.screenshot(path=f"{out}_{s:03d}.png")
            if len(sys.argv)>4 and str(s) in sys.argv[4].split(','):
                await pg.mouse.click(512,400)
                for k in ['Space','Enter']: await pg.keyboard.press(k); await pg.wait_for_timeout(300)
        open(out+'_log.txt','w').write('\n'.join(logs[-80:]))
        await b.close()
asyncio.run(main())
