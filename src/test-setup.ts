import { vi } from "vitest";

// Mock @decky/api
vi.mock("@decky/api", () => {
  const callFn = vi.fn();
  return {
    call: callFn,
    callable: vi.fn((name: string) => (...args: any[]) => callFn(name, ...args)),
    definePlugin: vi.fn((fn: any) => fn),
    routerHook: { addRoute: vi.fn(), removeRoute: vi.fn() },
    toaster: { toast: vi.fn() },
  };
});

// Mock @decky/ui
vi.mock("@decky/ui", () => ({
  ButtonItem: ({ children, onClick, description }: any) => {
    const React = require("react");
    return React.createElement("button", { onClick, "data-description": description }, children);
  },
  PanelSection: ({ children, title }: any) => {
    const React = require("react");
    return React.createElement("div", { "data-testid": "panel-section", "data-title": title }, children);
  },
  PanelSectionRow: ({ children }: any) => {
    const React = require("react");
    return React.createElement("div", { "data-testid": "panel-row" }, children);
  },
  Focusable: ({ children, style }: any) => {
    const React = require("react");
    return React.createElement("div", { style }, children);
  },
  TextField: ({ label, value, onChange }: any) => {
    const React = require("react");
    return React.createElement("input", { "aria-label": label, value, onChange, "data-testid": `textfield-${label}` });
  },
  ToggleField: ({ label, checked, onChange }: any) => {
    const React = require("react");
    return React.createElement("input", {
      type: "checkbox",
      "aria-label": label,
      checked,
      onChange: (e: any) => onChange(e.target.checked),
    });
  },
  SliderField: ({ label, value, onChange, min, max }: any) => {
    const React = require("react");
    return React.createElement("input", {
      type: "range",
      "aria-label": label,
      value,
      min,
      max,
      onChange: (e: any) => onChange(Number(e.target.value)),
    });
  },
  DropdownItem: ({ label, rgOptions, selectedOption, onChange }: any) => {
    const React = require("react");
    return React.createElement("select", {
      "aria-label": label,
      value: selectedOption,
      onChange: (e: any) => {
        const opt = rgOptions.find((o: any) => String(o.data) === e.target.value);
        if (opt) onChange(opt);
      },
    }, rgOptions?.map((opt: any) =>
      React.createElement("option", { key: String(opt.data), value: String(opt.data) }, opt.label)
    ));
  },
  ProgressBarItem: ({ nProgress, indeterminate, label }: any) => {
    const React = require("react");
    return React.createElement("div", {
      "data-testid": "progress-bar",
      "data-progress": nProgress,
      "data-indeterminate": indeterminate,
    }, label);
  },
  definePlugin: vi.fn((fn: any) => fn),
}));

// Mock react-icons
vi.mock("react-icons/fa", () => ({
  FaVideo: () => null,
  FaWifi: () => null,
  FaYoutube: () => null,
  FaCut: () => null,
  FaBroadcastTower: () => null,
  FaCog: () => null,
}));
