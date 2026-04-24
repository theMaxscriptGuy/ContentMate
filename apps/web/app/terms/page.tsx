import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Use | ContentMatePro",
  description: "Terms of Use for ContentMatePro",
  alternates: {
    canonical: "/terms"
  },
  robots: {
    index: false,
    follow: true
  }
};

const sections = [
  {
    title: "1. Acceptance",
    body: [
      "These Terms govern your access to and use of ContentMatePro, including our website, application, APIs, AI-assisted content strategy tools, analytics, generated content, and related services. By using the Service, you agree to these Terms."
    ]
  },
  {
    title: "2. Eligibility and Accounts",
    body: [
      "You must be legally able to enter into a binding agreement to use the Service. You are responsible for all activity under your account and for keeping your login credentials and devices secure.",
      "The Service may require Google Sign-In. You agree to provide accurate account information and comply with Google's applicable terms and policies."
    ]
  },
  {
    title: "3. Acceptable Use",
    body: [
      "You must not use the Service to violate law or third-party rights, upload or process data you do not have the right to use, generate illegal or infringing content, process sensitive regulated data without a separate written agreement, interfere with the Service, circumvent rate limits or security controls, or publish outputs without appropriate human review."
    ]
  },
  {
    title: "4. User Inputs and Required Rights",
    body: [
      "You are responsible for all URLs, prompts, content, files, instructions, brand materials, data, feedback, and other materials you submit or make available to the Service.",
      "You represent and warrant that you own or have all necessary rights to your submitted data, that it does not violate law or third-party rights, and that you have obtained all required consents, notices, permissions, and licenses."
    ]
  },
  {
    title: "5. Data Rights and ContentMatePro Ownership",
    body: [
      "To the maximum extent permitted by law, you grant ContentMatePro a worldwide, perpetual, irrevocable, transferable, sublicensable, royalty-free, fully paid license to host, store, reproduce, modify, adapt, transform, analyze, process, display, transmit, distribute, create derivative works from, commercialize, and otherwise use submitted data to provide and improve the Service; generate and store outputs; develop products, analytics, features, datasets, benchmarks, and AI workflows; maintain security and compliance; and create aggregated, anonymized, de-identified, derived, or statistical data.",
      "Where applicable law allows assignment of rights in submitted data, you agree that rights in data submitted to, processed by, or generated within the Service may be assigned to ContentMatePro to the maximum extent permitted. Where assignment is not legally effective, the license above applies as broadly as permitted.",
      "As between you and ContentMatePro, ContentMatePro owns the Service and all software, systems, workflows, prompts, templates, designs, databases, infrastructure, generated analyses, recommendations, content ideas, reports, strategies, calendars, metadata, scoring, classifications, logs, usage records, operational data, analytics, derived data, aggregated data, de-identified data, improvements, benchmarks, datasets, and learnings created from operation of the Service.",
      "Subject to your compliance with these Terms, ContentMatePro grants you a limited, revocable, non-exclusive, non-transferable permission to use Service outputs for your internal or commercial content planning purposes. This does not transfer ownership of the Service, platform, underlying systems, analytics, datasets, derived data, or ContentMatePro intellectual property.",
      "Nothing in these Terms limits rights that cannot legally be waived or transferred."
    ]
  },
  {
    title: "6. AI Outputs",
    body: [
      "AI-generated outputs may be inaccurate, incomplete, duplicative, offensive, unsafe, unsuitable, or legally sensitive. You are solely responsible for reviewing, editing, fact-checking, clearing rights for, and approving outputs before use or publication.",
      "ContentMatePro does not guarantee that outputs are unique, copyrightable, non-infringing, accurate, lawful, commercially successful, or suitable for any purpose."
    ]
  },
  {
    title: "7. Third-Party Content and Platforms",
    body: [
      "The Service may analyze public YouTube channels, public metadata, public captions, public transcripts, thumbnails, descriptions, and other public signals. Third-party platforms and content owners retain any rights they have in their materials. You are responsible for complying with third-party terms."
    ]
  },
  {
    title: "8. Plans, Limits, and Availability",
    body: [
      "We may impose usage limits, daily limits, quotas, rate limits, feature limits, or access restrictions. We may change, suspend, or discontinue any part of the Service at any time.",
      "The Service may include a free daily analysis allowance, promotional access, voucher-based access, credits, or other entitlements that govern how many analyses or features a user may use.",
      "Unless we explicitly state otherwise in writing, credits, vouchers, promotional entitlements, and similar access grants may be limited, suspended, revoked, changed, withdrawn, non-transferable, or non-refundable, and do not create a property right, stored-value right, bank account, or monetary balance.",
      "The current Service may limit users to two free analyses per user per day, with additional access available through promotional or credit-based mechanisms where offered."
    ]
  },
  {
    title: "9. Fees",
    body: [
      "If paid plans are introduced, you agree to pay all applicable fees, taxes, and charges. Fees may be non-refundable except where required by law or expressly stated in a separate written agreement.",
      "If we later offer paid credit packs, subscriptions, or usage-based access, additional purchase terms, billing terms, refund rules, and payment-processor terms may apply."
    ]
  },
  {
    title: "10. Disclaimers and Liability",
    body: [
      "The Service is provided as is and as available. To the maximum extent permitted by law, ContentMatePro disclaims all warranties, express or implied, including warranties of merchantability, fitness for a particular purpose, non-infringement, accuracy, availability, and reliability.",
      "To the maximum extent permitted by law, ContentMatePro will not be liable for indirect, incidental, special, consequential, exemplary, punitive, or lost-profit damages, or for loss of data, goodwill, business, revenue, or content.",
      "To the maximum extent permitted by law, ContentMatePro's total liability for all claims relating to the Service will not exceed the greater of the amount you paid ContentMatePro for the Service in the three months before the claim or INR 5,000."
    ]
  },
  {
    title: "11. Indemnity and Termination",
    body: [
      "You agree to defend, indemnify, and hold harmless ContentMatePro and its owners, operators, affiliates, service providers, contractors, and agents from claims, damages, liabilities, losses, costs, and expenses arising from your use of the Service, submitted data, outputs, publications, violation of these Terms, or violation of law or third-party rights.",
      "We may suspend or terminate access to the Service at any time if we believe you violated these Terms, created risk, caused harm, or used the Service in a way that may expose us or others to liability."
    ]
  },
  {
    title: "12. Governing Law, Changes, and Contact",
    body: [
      "These Terms are intended to be governed by the laws of India, unless a different governing law is required by applicable consumer protection or data protection law. Venue and dispute provisions should be finalized by counsel before commercial launch.",
      "We may update these Terms from time to time. Continued use of the Service after changes become effective means you accept the updated Terms.",
      "Contact ContentMatePro at create@contentmatepro.com."
    ]
  }
];

export default function TermsPage() {
  return (
    <main className="shell legalShell">
      <article className="legalPage">
        <Link className="legalBack" href="/">
          ContentMatePro
        </Link>
        <p className="sectionLabel">Legal</p>
        <h1>Terms of Use</h1>
        <p className="legalDate">Effective Date: April 23, 2026</p>
        <p className="legalIntro">
          These Terms govern your access to and use of ContentMatePro. They are prepared
          as a strong operational draft for legal review before broad commercial launch.
        </p>
        {sections.map((section) => (
          <section key={section.title}>
            <h2>{section.title}</h2>
            {section.body.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </section>
        ))}
        <div className="legalFooterLinks">
          <Link href="/privacy">Privacy Policy</Link>
          <a href="mailto:create@contentmatepro.com">create@contentmatepro.com</a>
        </div>
      </article>
    </main>
  );
}
