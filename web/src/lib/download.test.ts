import { afterEach, describe, expect, it, vi } from "vitest";
import { downloadText } from "./download";

afterEach(() => vi.restoreAllMocks());

describe("downloadText", () => {
  it("creates an object URL, clicks a download anchor, and revokes the URL", () => {
    const created: Blob[] = [];
    const create = vi.fn((b: Blob) => {
      created.push(b);
      return "blob:fake";
    });
    const revoke = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: create, revokeObjectURL: revoke });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    downloadText("report.html", "<!doctype html>", "text/html");

    expect(create).toHaveBeenCalledOnce();
    expect(created[0].type).toBe("text/html");
    const anchor = click.mock.instances[0] as HTMLAnchorElement;
    expect(anchor.download).toBe("report.html");
    expect(anchor.href).toBe("blob:fake");
    expect(revoke).toHaveBeenCalledWith("blob:fake");
  });
});
