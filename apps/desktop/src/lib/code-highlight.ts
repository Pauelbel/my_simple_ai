import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { tags } from '@lezer/highlight'

export const codeHighlight = syntaxHighlighting(HighlightStyle.define([
  { tag: [tags.comment, tags.meta], color: 'var(--syntax-comment)', fontStyle: 'italic' },
  { tag: [tags.keyword, tags.atom, tags.bool], color: 'var(--syntax-keyword)' },
  { tag: [tags.string, tags.special(tags.string), tags.regexp], color: 'var(--syntax-string)' },
  { tag: [tags.number, tags.literal, tags.escape], color: 'var(--syntax-number)' },
  { tag: [tags.typeName, tags.className, tags.namespace], color: 'var(--syntax-type)' },
  { tag: [tags.function(tags.variableName), tags.function(tags.propertyName), tags.tagName], color: 'var(--syntax-function)' },
  { tag: [tags.propertyName, tags.attributeName, tags.operator], color: 'var(--syntax-property)' },
  { tag: tags.invalid, color: 'var(--crepe-color-error)', textDecoration: 'underline wavy' },
]))
