interface Props {
  role: 'user' | 'assistant';
  content: string;
}

export function MessageBubble({ role, content }: Props) {
  const formatted = content
    .replace(
      /\[Source: ([^\]]+)\]/g,
      '<span class="inline-flex items-center gap-1 bg-blue-50 text-blue-700 text-xs font-medium px-2 py-0.5 rounded border border-blue-200 mx-0.5">📄 $1</span>'
    )
    .replace(/\n/g, '<br/>');

  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start gap-3">
      <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-sm flex-shrink-0 mt-1">
        🗽
      </div>
      <div
        className="max-w-[80%] bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed text-gray-800 shadow-sm"
        dangerouslySetInnerHTML={{ __html: formatted }}
      />
    </div>
  );
}
