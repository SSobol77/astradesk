import Card from '@/components/primitives/Card';

export default function JsonViewer({ value }: { value: unknown }) {
  return (
    <Card className="overflow-x-auto bg-slate-900 text-slate-100">
      <pre className="whitespace-pre-wrap break-words text-xs leading-5 text-[#2978B3]">
        {JSON.stringify(value, null, 2)}
      </pre>
    </Card>
  );
}
