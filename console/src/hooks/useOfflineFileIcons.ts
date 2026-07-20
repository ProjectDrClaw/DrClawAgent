/**
 * Replace ALL @agentscope-ai/chat CDN images with local offline assets.
 */

const CDN_MAP: Record<string, string> = {
  "https://gw.alicdn.com/imgextra/i1/O1CN01cVtZXI23tPVhiZoPJ_!!6000000007313-55-tps-40-40.svg":
    "/icons/file-xlsx.svg",
  "https://gw.alicdn.com/imgextra/i1/O1CN01uDnnuz1XMNEjgFMul_!!6000000002909-55-tps-40-40.svg":
    "/icons/file-image.svg",
  "https://gw.alicdn.com/imgextra/i1/O1CN01PaXli01DDPAO68fsI_!!6000000000182-55-tps-40-40.svg":
    "/icons/file-md.svg",
  "https://gw.alicdn.com/imgextra/i3/O1CN01mB5PzD27fuIWK661W_!!6000000007825-55-tps-40-40.svg":
    "/icons/file-pdf.svg",
  "https://gw.alicdn.com/imgextra/i3/O1CN01a8j7Jv1nW1QyFme7k_!!6000000005096-55-tps-40-40.svg":
    "/icons/file-ppt.svg",
  "https://gw.alicdn.com/imgextra/i1/O1CN01XaNi8P1UkhQXoQdUL_!!6000000002556-55-tps-40-40.svg":
    "/icons/file-doc.svg",
  "https://gw.alicdn.com/imgextra/i1/O1CN01K7jgEj1sywWTkPSGY_!!6000000005836-55-tps-40-40.svg":
    "/icons/file-zip.svg",
  "https://gw.alicdn.com/imgextra/i2/O1CN01zTTe0q1Xg4GkZgJol_!!6000000002952-55-tps-40-40.svg":
    "/icons/file-video.svg",
  "https://gw.alicdn.com/imgextra/i2/O1CN01qOBdXG1UpHO6f3Vvc_!!6000000002566-55-tps-40-40.svg":
    "/icons/file-audio.svg",
  "https://img.alicdn.com/imgextra/i3/O1CN01822qqr1PVyaK7MYtn_!!6000000001847-2-tps-40-40.png":
    "/icons/welcome-prompt.png",
  "https://gw.alicdn.com/imgextra/i3/O1CN01822qqr1PVyaK7MYtn_!!6000000001847-2-tps-40-40.png":
    "/icons/welcome-prompt.png",
};

const CDN_REFS = Object.keys(CDN_MAP);

function getLocalUrl(url: string): string | null {
  if (CDN_MAP[url]) return CDN_MAP[url];
  for (const cdn of CDN_REFS) {
    if (url.endsWith(cdn)) return CDN_MAP[cdn];
  }
  const m = url.match(
    /(?:gw|img)\.alicdn\.com\/imgextra\/([^?#&]+?)(?:\.(?:svg|png|apng|jpg|jpeg|gif))$/i,
  );
  if (m) {
    const full = url.substring(0, url.indexOf(m[1]) + m[1].length);
    const n = full.replace("img.alicdn.com", "gw.alicdn.com");
    return CDN_MAP[n] ?? CDN_MAP[full] ?? null;
  }
  return null;
}

// Patch HTMLImageElement.src
{
  const desc = Object.getOwnPropertyDescriptor(
    HTMLImageElement.prototype,
    "src",
  );
  if (desc && desc.set && desc.get) {
    const origSet = desc.set;
    const origGet = desc.get;
    Object.defineProperty(HTMLImageElement.prototype, "src", {
      get(this: HTMLImageElement) {
        return (origGet!.call(this) as string) || "";
      },
      set(this: HTMLImageElement, val: string) {
        return (origSet!.call(this, getLocalUrl(val) ?? val) as void) ?? null;
      },
      configurable: true,
      enumerable: true,
    });
  }
}

// Patch setAttribute
{
  const origAttr = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function (
    this: Element,
    attr: string,
    val: string,
  ) {
    if (this instanceof HTMLImageElement && attr.toLowerCase() === "src") {
      const local = getLocalUrl(val);
      if (local) {
        (this as HTMLImageElement).src = local;
        return;
      }
    }
    return origAttr.call(this, attr, val);
  };
}

function replaceImages() {
  try {
    document.querySelectorAll<HTMLImageElement>("img").forEach((img) => {
      const src = img.getAttribute("src");
      if (src) {
        const local = getLocalUrl(src);
        if (local) img.src = local;
      }
    });
  } catch (_) {}
}

replaceImages();
setTimeout(() => replaceImages(), 50);
setTimeout(() => replaceImages(), 200);
setTimeout(() => replaceImages(), 500);

try {
  const OrigMO = window.MutationObserver;
  window.MutationObserver = function (cb: MutationCallback) {
    const wrapped = (mutations: MutationRecord[], obs: MutationObserver) => {
      replaceImages();
      return cb(mutations, obs);
    };
    return new OrigMO(wrapped);
  } as any;
} catch (_) {}
