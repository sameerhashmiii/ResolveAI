export interface DemoScenario {
  slug: string
  title: string
  description: string
  requesterName: string
  requesterDepartment: string
  location: string
  device: string
  application: string
  expectedOutcome: string
  recommended?: boolean
}

export const demoScenarios: DemoScenario[] = [
  {
    slug: 'dallas-vpn-payrollpro-dns',
    title: 'VPN works, PayrollPro does not',
    description:
      'The VPN connects from Dallas, but PayrollPro remains unavailable and its internal service name does not resolve. Other internet services work.',
    requesterName: 'Jordan Lee',
    requesterDepartment: 'Payroll',
    location: 'Dallas',
    device: 'SYN-DEV-00041',
    application: 'PayrollPro',
    expectedOutcome:
      'Healthy VPN and degraded DNS evidence support a probable, not confirmed, cause that an analyst can complete.',
    recommended: true,
  },
  {
    slug: 'microsoft-365-outlook',
    title: 'Outlook cannot sync Microsoft 365 mail',
    description:
      'Outlook stopped syncing Microsoft 365 mail this morning. Web access works, but the desktop client repeatedly asks to reconnect.',
    requesterName: 'Morgan Chen',
    requesterDepartment: 'Finance',
    location: 'New York',
    device: 'SYN-DEV-00118',
    application: 'Microsoft 365 / Outlook',
    expectedOutcome:
      'Client and service evidence remain distinct; confidence describes evidence support, not measured accuracy.',
  },
  {
    slug: 'chicago-wifi',
    title: 'Intermittent Wi-Fi in Chicago',
    description:
      'The laptop disconnects from office Wi-Fi several times an hour on the Chicago third floor. Nearby colleagues remain connected.',
    requesterName: 'Riley Patel',
    requesterDepartment: 'Operations',
    location: 'Chicago',
    device: 'SYN-DEV-00207',
    application: 'Corporate Wi-Fi',
    expectedOutcome:
      'Bounded device and network observations show what is known and what still needs human verification.',
  },
  {
    slug: 'password-mfa-handoff',
    title: 'Password reset blocked by MFA',
    description:
      'The requester changed phones and cannot complete MFA after a password reset. They need access restored without bypassing identity controls.',
    requesterName: 'Casey Williams',
    requesterDepartment: 'People Operations',
    location: 'Remote',
    device: 'SYN-DEV-00312',
    application: 'Identity portal',
    expectedOutcome:
      'The evidence indicates a manager handoff; no role escalation or account action occurs automatically.',
  },
  {
    slug: 'application-outage',
    title: 'Shared PayrollPro application outage',
    description:
      'Multiple users report that PayrollPro returns a service unavailable message. The issue began at approximately 14:10 local time.',
    requesterName: 'Taylor Brooks',
    requesterDepartment: 'Customer Operations',
    location: 'Atlanta',
    device: 'SYN-DEV-00444',
    application: 'PayrollPro',
    expectedOutcome:
      'Service and incident evidence establish scope while remediation and incident decisions stay with people.',
  },
]

export function getDemoScenario(slug: string | null) {
  return demoScenarios.find((scenario) => scenario.slug === slug)
}
