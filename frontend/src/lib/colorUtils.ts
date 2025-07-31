export function getBrightness(color: string) {
  const rgb = color.match(/\w\w/g)?.map((c) => parseInt(c, 16)) ?? [0, 0, 0];
  const [r = 0, g = 0, b = 0] = rgb;
  return r * 0.299 + g * 0.587 + b * 0.114;
}

export function getHue(color: string) {
  const rgb = color.match(/\w\w/g)?.map((c) => parseInt(c, 16)) ?? [0, 0, 0];
  const [r = 0, g = 0, b = 0] = rgb;
  return Math.atan2(b - g, r - g);
}
