import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | ContentMatePro",
  description: "Privacy Policy for ContentMatePro",
  alternates: {
    canonical: "/privacy"
  },
  robots: {
    index: false,
    follow: true
  }
};

const sections = [
  {
    title: "1. Who We Are",
    body: [
      "ContentMatePro provides AI-assisted YouTube channel analysis, transcript and metadata processing, creator strategy insights, content ideation, and related content generation workflows.",
      "Contact us at create@contentmatepro.com."
    ]
  },
  {
    title: "2. Information We Collect",
    body: [
      "We may collect Google Sign-In account information such as your Google account identifier, email address, display name, profile image, and login status.",
      "We may collect YouTube channel URLs, public video URLs, prompts, notes, content briefs, drafts, titles, descriptions, scripts, hooks, files, feedback, and support communications that you submit.",
      "We may collect public YouTube channel metadata, public video metadata, thumbnails, durations, counts, captions, subtitles, or transcripts where accessible.",
      "We may collect generated outputs such as channel analysis, topic insights, content strategy recommendations, video ideas, shorts ideas, thumbnail concepts, and content calendars.",
      "We may collect usage, device, log, analytics, security, diagnostic, and performance data."
    ]
  },
  {
    title: "3. How We Use Information",
    body: [
      "We use information to provide, operate, secure, maintain, and improve the Service; authenticate users; process YouTube URLs and public metadata; generate analyses and content ideas; store user history; enforce usage limits; prevent abuse; debug errors; provide support; develop new features; create aggregated or de-identified data; comply with law; and enforce our rights."
    ]
  },
  {
    title: "4. Data Rights, Ownership, and License",
    body: [
      "You represent that you have all rights, permissions, licenses, consents, and authority necessary to submit any content, data, prompts, files, URLs, materials, or information to the Service.",
      "To the maximum extent permitted by law, by submitting data to the Service, you grant ContentMatePro a worldwide, perpetual, irrevocable, transferable, sublicensable, royalty-free, fully paid license to host, store, reproduce, modify, adapt, transform, analyze, process, display, transmit, distribute, create derivative works from, commercialize, and otherwise use that data to provide, operate, improve, secure, and develop the Service.",
      "Where applicable law allows assignment of rights in submitted data, you agree that rights in data submitted to, processed by, or generated within the Service may be assigned to ContentMatePro to the maximum extent permitted. Where assignment is not legally effective, the license above applies as broadly as permitted.",
      "As between you and ContentMatePro, ContentMatePro owns the Service, platform, software, workflows, prompts, templates, systems, designs, databases, infrastructure, service-generated metadata, logs, usage records, analytics, classifications, derived data, aggregated data, de-identified data, generated reports, recommendations, strategies, and service improvements.",
      "This section does not limit non-waivable privacy, consumer protection, data protection, publicity, moral, or other rights that cannot legally be waived or transferred."
    ]
  },
  {
    title: "5. AI and Content Generation",
    body: [
      "The Service uses artificial intelligence and automated systems. AI-generated outputs may be inaccurate, incomplete, similar to other content, unsuitable for a particular purpose, or legally sensitive depending on use. You are responsible for reviewing, editing, validating, and approving outputs before publication or commercial use.",
      "We may use third-party AI providers to process inputs and generate outputs."
    ]
  },
  {
    title: "6. How We Share Information",
    body: [
      "We may share information with hosting, database, storage, analytics, authentication, AI, error monitoring, logging, security, payment, professional advisory, legal, compliance, and operational providers as needed to provide and improve the Service.",
      "We may share information where required by law or in connection with a merger, acquisition, financing, reorganization, bankruptcy, sale of assets, or similar transaction.",
      "We do not sell Google user data. We do not use Google user data for personalized advertising."
    ]
  },
  {
    title: "7. Cookies and Analytics",
    body: [
      "We may use cookies, local storage, tokens, pixels, scripts, analytics tools, and similar technologies to keep users signed in, store application state, measure usage and performance, secure the Service, and detect errors or abuse."
    ]
  },
  {
    title: "8. Retention and Security",
    body: [
      "We may retain information for as long as reasonably necessary to provide user history, operate and improve the Service, maintain security, prevent fraud, debug issues, comply with legal obligations, resolve disputes, and enforce agreements.",
      "We may retain aggregated, anonymized, de-identified, derived, or statistical data indefinitely where permitted by law.",
      "We use reasonable administrative, technical, and organizational safeguards designed to protect information, but no online service can guarantee absolute security."
    ]
  },
  {
    title: "9. Your Choices and Rights",
    body: [
      "Depending on your location, you may have rights to request access, correction, deletion, portability, restriction, objection, withdrawal of consent, or information about how your personal information is processed.",
      "To make a request, contact create@contentmatepro.com. We may need to verify your identity before responding."
    ]
  },
  {
    title: "10. Children and Sensitive Data",
    body: [
      "The Service is not intended for children under 13 or for users below the minimum age required by applicable law.",
      "The Service is not designed for processing sensitive regulated data such as medical records, financial account credentials, government identifiers, biometric data, precise geolocation, protected health information, payment card data, or legally privileged information unless we have entered into a separate written agreement specifically allowing it."
    ]
  },
  {
    title: "11. Changes and Contact",
    body: [
      "We may update this Privacy Policy from time to time. The updated version will be posted with a new effective date.",
      "For privacy questions, requests, or complaints, contact ContentMatePro at create@contentmatepro.com."
    ]
  }
];

export default function PrivacyPage() {
  return (
    <main className="shell legalShell">
      <article className="legalPage">
        <Link className="legalBack" href="/">
          ContentMatePro
        </Link>
        <p className="sectionLabel">Legal</p>
        <h1>Privacy Policy</h1>
        <p className="legalDate">Effective Date: April 23, 2026</p>
        <p className="legalIntro">
          This Privacy Policy explains how ContentMatePro collects, uses, stores, shares,
          and protects information when you access or use our website, application, APIs,
          artificial intelligence features, analytics, and related services.
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
          <Link href="/terms">Terms of Use</Link>
          <a href="mailto:create@contentmatepro.com">create@contentmatepro.com</a>
        </div>
      </article>
    </main>
  );
}
