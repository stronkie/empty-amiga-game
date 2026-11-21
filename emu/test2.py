import asyncio,json,sys
from playwright.async_api import async_playwright
adf,out,shots,acts=sys.argv[1],sys.argv[2],[int(x) for x in sys.argv[3].split(',')],sys.argv[4] if len(sys.argv)>4 else ''
A={}
for a in filter(None,acts.split(';')):
    t,k=a.split(':');A[int(t)]=k.split(',')
cfg={"url":f"http://127.0.0.1:8000/games/{adf}","AROS":True,"port2":True,"navbar":False,"dialog_on_missing_roms":False,"dialog_on_disk":False}
url="http://127.0.0.1:8000/index.html#"+json.dumps(cfg)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--autoplay-policy=no-user-gesture-required','--use-gl=swiftshader','--enable-unsafe-swiftshader'])
        pg=await b.new_page(viewport={'width':1024,'height':800})
        await pg.goto(url)
        ev=sorted(set(shots)|set(A));t=0
        for s in ev:
            await pg.wait_for_timeout((s-t)*1000);t=s
            if s in A:
                await pg.mouse.click(512,400)
                for k in A[s]:
                    await pg.keyboard.down(k);await pg.wait_for_timeout(150);await pg.keyboard.up(k);await pg.wait_for_timeout(250)
            if s in shots: await pg.screenshot(path=f"{out}_{s:03d}.png")
        await b.close()
asyncio.run(main())
