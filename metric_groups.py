groups = {
  'Octets': ['InOctets','OutOctets'],
  'Packets': ['InUcastPkts',
              'InMulticastPkts',
              'InBroadcastPkts',
              'OutUcastPkts',
              'OutMulticastPkts',
              'OutBroadcastPkts',
  ],
  'Errors': ['InErrors','InDiscards','OutErrors','OutDiscards',],
}
metric_map = {
  'InOctets': 'Octets',
  'OutOctets': 'Octets',
  'InUcastPkts': 'Packets',
  'InMulticastPkts': 'Packets',
  'InBroadcastPkts': 'Packets',
  'OutUcastPkts': 'Packets',
  'OutMulticastPkts': 'Packets',
  'OutBroadcastPkts': 'Packets',
  'InErrors': 'Errors',
  'InDiscards': 'Errors',
  'OutErrors': 'Errors',
  'OutDiscards': 'Errors',
}
