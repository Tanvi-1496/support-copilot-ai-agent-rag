import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function Answer({ text }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
}
