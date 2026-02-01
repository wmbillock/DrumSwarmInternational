export interface TabItem {
  key: string;
  label: string;
}

interface TabsProps {
  active: string;
  onChange: (key: string) => void;
  items: TabItem[];
}

export function Tabs({ active, onChange, items }: TabsProps) {
  return (
    <div className="ui-tabs">
      {items.map((item) => (
        <button
          key={item.key}
          className={`tab ${active === item.key ? "active" : ""}`}
          onClick={() => onChange(item.key)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
