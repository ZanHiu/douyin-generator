export interface VoiceOption {
  id: string
  name: string
  meta: string
}

export const voiceOptions: VoiceOption[] = [
  { id: 'banmai', name: 'Ban Mai', meta: 'Northern female' },
  { id: 'thuminh', name: 'Thu Minh', meta: 'Northern female' },
  { id: 'lannhi', name: 'Lan Nhi', meta: 'Southern female' },
  { id: 'linhsan', name: 'Linh San', meta: 'Southern female' },
  { id: 'leminh', name: 'Le Minh', meta: 'Northern male' },
  { id: 'giahuy', name: 'Gia Huy', meta: 'Central male' },
  { id: 'myan', name: 'My An', meta: 'Central female' }
]
