import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CatalogProvider, Provider } from "@/types";

vi.mock("@/api", () => ({ api: { saveProvider: vi.fn() } }));
import { api } from "@/api";
import { ConnectCard } from "./ConnectCard";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const provider: CatalogProvider = {
  id: "openai", label: "OpenAI", connected: false, fields: [{ id: "api_key", env_var: "OPENAI_API_KEY", required: true }],
};
const details = {
  id: "openai", configured: false,
  fields: [{ id: "api_key", env_var: "OPENAI_API_KEY", configured: false }],
} as unknown as Provider;

describe("ConnectCard", () => {
  it("saves a password once, clears it, and exposes the env var only as a tooltip", async () => {
    const onConnected = vi.fn();
    vi.mocked(api.saveProvider).mockResolvedValue(details);
    render(<ConnectCard provider={provider} onConnected={onConnected} />);

    const input = screen.getByLabelText("API key — OpenAI");
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("autoComplete", "off");
    expect(input).toHaveAttribute("title", "OPENAI_API_KEY");
    expect(screen.queryByText("OPENAI_API_KEY")).not.toBeInTheDocument();

    await userEvent.type(input, "secret-value");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(api.saveProvider).toHaveBeenCalledWith("openai", { api_key: "secret-value" });
    expect(onConnected).toHaveBeenCalledOnce();
    expect(input).toHaveValue("");
    expect(screen.queryByText("secret-value")).not.toBeInTheDocument();
  });

  it("shows the no-key state, hint, and default URL for Ollama", () => {
    const ollama: CatalogProvider = {
      id: "ollama", label: "Ollama (local)", connected: true,
      fields: [{ id: "base_url", env_var: "OLLAMA_BASE_URL", required: false }],
    };

    render(<ConnectCard provider={ollama} onConnected={vi.fn()} />);

    expect(screen.getByText("no key needed")).toBeInTheDocument();
    expect(screen.getByText(/Runs against http:\/\/localhost:11434 by default/)).toBeInTheDocument();
    expect(screen.getByLabelText("base URL — Ollama (local)")).toHaveAttribute("placeholder", "http://localhost:11434/v1");
  });

  it("shows the URL state and server hint for an unconnected MLX server", () => {
    const mlx: CatalogProvider = {
      id: "mlx", label: "MLX or another OpenAI-compatible server", connected: false,
      fields: [{ id: "base_url", env_var: "MLX_BASE_URL", required: true }],
    };

    render(<ConnectCard provider={mlx} onConnected={vi.fn()} />);

    expect(screen.getByText("URL")).toBeInTheDocument();
    expect(screen.getByText(/Start the server \(for example mlx_lm.server/)).toBeInTheDocument();
    expect(screen.getByLabelText("base URL — MLX or another OpenAI-compatible server")).toHaveAttribute("placeholder", "http://localhost:8090/v1");
  });
});
