---
name: promo-video-workflow
description: 把中文长文案、产品介绍、图文教程、充值流程、销售页、优惠活动、二维码和 CTA 素材制作成 HyperFrames 宣传视频。适用于用户要求根据文章或营销文案生成视频、拆分视频分镜、生成逐场景配音、使用 milorapart TTS API 生成音频、按真实音频时长调整视频节奏、插入音频轨道、校验并渲染 MP4 的任务。
---

# 宣传视频工作流

用这个 skill 把密集的中文宣传文案，整理成可渲染的 HyperFrames 视频，并配上按场景同步的中文旁白。

使用本 skill 时，同时使用 `hyperframes` 和 `hyperframes-cli` skill。凡是改动 `.html` composition，完成前必须运行 `npm run check`。

## 核心原则

**让配音决定节奏，画面跟着声音走。**

不要把整段旁白一次性生成，再强行塞进固定时长的视频。正确做法是按 scene 拆句，每个 scene 生成一段音频，测出真实时长，再调整 scene 的 `data-start`、`data-duration`、动画时间和转场时间。

## 工作流

### 1. 提取宣传要点

从用户给的长文案中提取：

- 产品或服务是什么
- 目标用户是谁
- 用户痛点是什么
- 解决方案是什么
- 操作流程是什么
- 保障、售后、质保是什么
- 额外权益是什么
- 最终 CTA 是什么

保持表述忠实于原文。第三方服务不要写成官方服务，除非原文明确支持。

远程图片、二维码和关键素材要下载到 `assets/`，不要让渲染依赖外链。

### 2. 拆成视频结构

大多数中文宣传片用 5-7 个 scene：

- Hook：开头问题、日期、强卖点或直接利益点
- Pain：用户痛点，通常 3-5 个
- Solution：服务如何解决问题
- Process：具体操作步骤
- Bonus：优惠券、API 额度、试用权益、开发者价值
- CTA：扫码、联系客服、回复关键词、领取优惠

不要把长文案整段搬进画面。视频里只保留每段最重要的信息。

### 3. 写每个 scene 的旁白

每个 scene 通常只写一句旁白。

原则：

- 旁白负责带节奏，不重复念完所有画面文字
- 一句话只服务一个 scene
- 太长就拆成多个 scene，或者延长当前 scene
- 需要明确读法时直接写出来，例如 `A P I`
- 数字、日期、英文缩写要按希望听到的方式写

示例：

```text
二零二六年五月二日，想开 GPT Plus，不用再折腾国际信用卡。
很多用户会卡在付款、Apple ID、礼品卡，或者担心充值不到账。
这套第三方充值流程，不交账号密码，支持微信和支付宝，订单、卡密和状态都能查询。
```

### 4. 先做无声版

先完成画面，再配音。

需要完成：

- 多 scene 结构
- 每个 timed 可见元素的 `data-start`、`data-duration`、`data-track-index`
- 可见 timed 元素使用 `class="clip"`
- GSAP timeline 使用 `{ paused: true }`
- 注册到 `window.__timelines`
- scene 之间有转场
- 二维码、截图、图片等资源本地化到 `assets/`
- 截图、二维码、产品图、教程图等关键图片必须完整展示，不能为了填满卡片使用会裁切内容的 `object-fit: cover`
- 普通截图优先用 `object-fit: contain`、`background-size: contain` 或等比缩放，确保上下左右边界都可见
- 长图、聊天记录、文章截图、手机长截屏必须自行滚动展示；根据原图尺寸、展示窗口尺寸和缩放比例计算需要滚动的距离
- 长图滚动时间可以冗余，但不能不够；顶部和底部都要留停留时间，让观众看清图的开始和结束
- 对长图滚动，建议用 `scroll distance = scaled image height - viewport height`，动画距离略大于该值但不要过度滚出主体内容

检查：

```bash
npm run check
```

### 5. 按句生成配音

使用 milorapart API。接口返回 JSON，里面有 mp3 地址。

推荐用 `curl -G --data-urlencode`，避免手动 URL 编码中文：

```bash
curl -G --fail \
  --data-urlencode "text=这里是一句旁白" \
  "https://api.milorapart.top/apis/mbAIsc" \
  -o /tmp/voice-01.json
```

返回格式类似：

```json
{
  "code": 200,
  "msg": "生成完成!",
  "url": "https://api.milorapart.top/voice/xxx.mp3"
}
```

提取 `url` 并下载：

```bash
URL=$(node -e "const fs=require('fs'); const r=JSON.parse(fs.readFileSync('/tmp/voice-01.json','utf8')); process.stdout.write(r.url)")
curl -L --fail "$URL" -o assets/voice-01.mp3
```

音频命名保持稳定：

- `assets/voice-01.mp3`
- `assets/voice-02.mp3`
- `assets/voice-03.mp3`

### 6. 测量每句真实时长

逐个检测音频，不要一次性把多个 mp3 传给同一个 `ffprobe`。

```bash
for f in assets/voice-*.mp3; do
  printf "%s " "$f"
  ffprobe -v error -show_entries format=duration -of csv=p=0 "$f"
done
```

每个 scene 的建议长度：

```text
scene duration = voice duration + 0.3s 到 0.8s 呼吸时间
```

流程复杂、CTA 或二维码 scene 可以多留一点时间。

### 7. 按音频重排时间轴

更新：

- root `data-duration`
- 每个 scene 的 `data-start`
- 每个 scene 的 `data-duration`
- 音频 `<audio>` 的 `data-start`
- GSAP 动画起始时间
- 转场时间
- 最终 fade 时间

推荐在主 timeline 里使用变量，不要到处写硬编码秒数：

```js
const s1 = 0;
const s2 = 6;
const s3 = 11.5;
const s4 = 19.6;
const s5 = 28;
const s6 = 37.2;
const end = 45;
```

转场通常放在：

```js
nextSceneStart - 0.25
```

动画时间写成：

```js
tl.fromTo(".s3-el", fromVars, toVars, s3 + 0.34);
```

避免写死成旧的全局时间，例如 `7.94`。

### 8. 插入独立音频轨道

每句旁白使用独立 `<audio>`：

```html
<audio
  id="voice-01"
  data-start="0.35"
  data-duration="5.52"
  data-track-index="20"
  src="assets/voice-01.mp3"
  data-volume="1"
></audio>
```

规则：

- 每句单独一个 audio
- 不要用 video 元素播放音频
- 每个 audio 用独立 track index
- `data-start` 对齐当前 scene 内旁白开始时间
- `data-duration` 使用真实 mp3 时长

### 9. 校验和渲染

运行：

```bash
npm run check
npm run render
```

渲染前后要抽帧确认关键图片：

- 对比截图、查询结果、二维码等静态图至少抽对应 scene 的一帧，确认图片没有被裁切
- 长图至少抽顶部、中段、底部三帧，确认滚动距离足够且底部内容出现过
- 如果发现图片只显示局部，要先改布局或滚动距离再重新 `npm run check` 和 `npm run render`

渲染后确认 MP4 时长和音频流：

```bash
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1:nokey=0 renders/<file>.mp4
ffprobe -v error -select_streams a -show_entries stream=codec_name,duration,channels -of default=noprint_wrappers=1:nokey=0 renders/<file>.mp4
```

如果看到 `audioCount` 大于 0，且最终 MP4 有 AAC 音频流，说明音频进入了渲染管线。

## 背景音乐和音效

先把旁白同步做好，再考虑音乐和音效。

建议：

- 旁白是主层
- 背景乐音量一般 `0.10` 到 `0.18`
- UI 音效只放在转场、卡片出现、CTA 显示等关键点
- 如果听起来拥挤，优先删音效，不要牺牲旁白清晰度

## 最终汇报

完成后向用户说明：

- 改了哪些 composition 文件
- 生成了哪些 `voice-xx.mp3`
- 最终 MP4 路径
- `npm run check` 是否通过
- 最终视频时长
- MP4 是否包含音频流

如果仍有 lint warning，要说明是阻塞问题还是旧文件/结构性非阻塞 warning。
