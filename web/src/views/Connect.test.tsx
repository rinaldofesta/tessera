import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Catalog, Provider } from "@/types";

vi.mock("@/api", () => ({ api: { catalog: vi.fn(), saveProvider: vi.fn() } }));
import { api } from "@/api";
import Connect from "./Connect";

const catalog: Catalog = {
  defaults: { engine: "deterministic", suite: "starter", k: 3, scaffold: "baseline", seed: 0 },
  suites: [], models: [], scorers: [], scaffolds: ["baseline"],
  providers: [
    { id: "openai", label: "OpenAI", connected: false, fields: [{ id: "api_key", env_var: "OPENAI_API_KEY", required: true }] },
    { id: "ollama", label: "Ollama (local)", connected: true, fields: [{ id: "base_url", env_var: "OLLAMA_BASE_URL", required: false }] },
    { id: "mlx", label: "MLX or another OpenAI-compatible server", connected: false, fields: [{ id: "base_url", env_var: "MLX_BASE_URL", required: true }] },
  ],
};
const details = [
  { id: "openai", configured: false, fields: [{ id: "api_key", env_var: "OPENAI_API_KEY", configured: false }] },
  { id: "mlx", configured: false, fields: [{ id: "base_url", env_var: "MLX_BASE_URL", configured: false }] },
] as unknown as Provider[];

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  vi.mocked(api.catalog).mockResolvedValue(catalog);
});

describe("Connect", () => {
  it("lists Ollama and MLX cards and saves without displaying credentials or env vars", async () => {
    vi.mocked(api.saveProvider).mockResolvedValue(details[0]);
    render(<MemoryRouter><Connect /></MemoryRouter>);

    expect(await screen.findByText("OpenAI")).toBeInTheDocument();
    expect(screen.getByText("Ollama (local)")).toBeInTheDocument();
    expect(screen.getByText("MLX or another OpenAI-compatible server")).toBeInTheDocument();
    expect(screen.getByLabelText("base URL — Ollama (local)")).toBeInTheDocument();
    expect(screen.getByLabelText("base URL — MLX or another OpenAI-compatible server")).toBeInTheDocument();
    const key = screen.getByLabelText("API key — OpenAI");
    expect(key).toHaveAttribute("title", "OPENAI_API_KEY");
    expect(screen.queryByText("OPENAI_API_KEY")).not.toBeInTheDocument();

    await userEvent.type(key, "secret-value");
    await userEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);
    expect(api.saveProvider).toHaveBeenCalledWith("openai", { api_key: "secret-value" });
    expect(key).toHaveValue("");
    expect(screen.queryByText("secret-value")).not.toBeInTheDocument();
  });
});
