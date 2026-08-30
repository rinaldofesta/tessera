/** Hand the browser a text file to save. The anchor is attached to the DOM for the
 *  click — some browsers won't fire a download from a detached element — then removed;
 *  the object URL is revoked after, once the download has had the tick it needs to start. */
export function downloadText(filename: string, text: string, mime: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
