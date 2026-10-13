
import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "▦" },
  { id: "employee", label: "Employee Portal", icon: "＋" },
  { id: "analysis", label: "AI Analysis", icon: "✦" },
  { id: "knowledge", label: "Knowledge Base", icon: "▤" },
  { id: "software", label: "Software Requests", icon: "▣" },
];

function errorMessage(data, fallback) {
  if (typeof data?.detail === "string") return data.detail;
  if (typeof data?.message === "string") return data.message;
  if (typeof data?.error === "string") return data.error;
  if (Array.isArray(data?.detail)) {
    return data.detail.map((x) => x.msg || String(x)).join(", ");
  }
  return fallback;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? String(value)
    : date.toLocaleString();
}

function softwareName(item) {
  if (typeof item === "string") return item;
  return item?.display_name || item?.name ||
    item?.software_name || item?.title || "Software";
}

function softwareId(item) {
  if (typeof item === "string") return item;
  return String(item?.id || item?.software_id ||
    item?.name || item?.display_name || "");
}

function App() {
  const [activePage, setActivePage] = useState("dashboard");

  const [tickets, setTickets] = useState([]);
  const [request, setRequest] = useState("");
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketSubmitting, setTicketSubmitting] = useState(false);
  const [ticketError, setTicketError] = useState("");
  const [ticketNotice, setTicketNotice] = useState("");

  const [selfHealLoadingId, setSelfHealLoadingId] = useState("");
  const [selfHealError, setSelfHealError] = useState("");
  const [selfHealNotice, setSelfHealNotice] = useState("");
  const [selfHealedIds, setSelfHealedIds] = useState([]);

  const [knowledgeQuestion, setKnowledgeQuestion] = useState("");
  const [knowledgeAnswer, setKnowledgeAnswer] = useState(null);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [knowledgeError, setKnowledgeError] = useState("");
  const [knowledgeArticles, setKnowledgeArticles] = useState([]);
  const [articlesLoading, setArticlesLoading] = useState(false);
  const [articlesError, setArticlesError] = useState("");

  const [softwareCatalogue, setSoftwareCatalogue] = useState([]);
  const [softwareRequests, setSoftwareRequests] = useState([]);
  const [selectedSoftware, setSelectedSoftware] = useState("");
  const [requestedBy, setRequestedBy] = useState("Employee");
  const [justification, setJustification] = useState("");
  const [softwareLoading, setSoftwareLoading] = useState(false);
  const [softwareSubmitting, setSoftwareSubmitting] = useState(false);
  const [softwareError, setSoftwareError] = useState("");
  const [softwareNotice, setSoftwareNotice] = useState("");

  const [auditRecords, setAuditRecords] = useState([]);
  const [auditError, setAuditError] = useState("");

  // ---------------- TICKETS ----------------

  const loadTickets = useCallback(async () => {
    setTicketsLoading(true);
    setTicketError("");

    try {
      const response = await fetch(`${API_URL}/api/tickets`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(errorMessage(data, "Could not load tickets."));
      }

      const list = Array.isArray(data)
        ? data
        : data?.tickets || data?.data || [];

      setTickets((previous) => {
        const previousById = new Map(
          previous.map((ticket) => [ticket.id, ticket])
        );

        return list.map((ticket) => {
          const id = String(ticket.id || ticket.ticket_id || "");
          const old = previousById.get(id);
          const resolved =
            selfHealedIds.includes(id) ||
            String(old?.status || "").toLowerCase().includes("resolved");

          return {
            ...ticket,
            id,
            title: ticket.summary || ticket.title ||
              ticket.description || "IT support request",
            status: resolved ? "Resolved" : ticket.status || "Open",
            category: ticket.category || "Unclassified",
            priority: ticket.priority || "P3",
            assignment_group: ticket.assignment_group || "Helpdesk",
          };
        }).filter((ticket) => ticket.id);
      });
    } catch (error) {
      console.error("Ticket loading error:", error);
      setTicketError(error.message || "Could not load tickets.");
    } finally {
      setTicketsLoading(false);
    }
  }, [selfHealedIds]);

  async function submitRequest(event) {
    event.preventDefault();
    if (!request.trim() || ticketSubmitting) return;

    setTicketSubmitting(true);
    setTicketError("");
    setTicketNotice("");

    try {
      const response = await fetch(`${API_URL}/api/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: request.trim() }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(errorMessage(data, "Ticket submission failed."));
      }

      const ticket = data.ticket || data;
      setTicketNotice(
        `Ticket ${ticket.id || ticket.ticket_id || ""} created successfully.`
      );
      setRequest("");
      await loadTickets();
    } catch (error) {
      setTicketError(error.message || "Unable to submit the ticket.");
    } finally {
      setTicketSubmitting(false);
    }
  }

  function getSelfHealAction(ticket) {
    const text = [
      ticket.title, ticket.description, ticket.category, ticket.subcategory,
    ].join(" ").toLowerCase();

    if (
      text.includes("password") ||
      text.includes("account locked") ||
      text.includes("locked out") ||
      text.includes("account unlock")
    ) {
      return { action: "account_unlock", label: "Account unlock" };
    }

    if (
      text.includes("vpn") ||
      text.includes("wi-fi") ||
      text.includes("wifi")
    ) {
      return { action: "vpn_restart", label: "VPN restart" };
    }

    return null;
  }

  async function handleSelfHeal(ticket) {
    const ticketId = String(ticket.id || "");
    const selectedAction = getSelfHealAction(ticket);

    if (!ticketId || selfHealLoadingId) return;

    if (String(ticket.status).toLowerCase().includes("resolved")) {
      setSelfHealError("This ticket is already resolved.");
      return;
    }

    if (!selectedAction) {
      setSelfHealError(
        "No supported mock action was identified. Please escalate to IT support."
      );
      return;
    }

    setSelfHealLoadingId(ticketId);
    setSelfHealError("");
    setSelfHealNotice("");

    try {
      const response = await fetch(`${API_URL}/api/self-heal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticket_id: ticketId,
          action: selectedAction.action,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(errorMessage(data, "Self-healing failed."));
      }

      if (data.status === "success") {
        setSelfHealedIds((current) =>
          current.includes(ticketId) ? current : [...current, ticketId]
        );
        setTickets((current) => current.map((item) =>
          item.id === ticketId
            ? { ...item, status: data.ticket_status || "Resolved" }
            : item
        ));
      } else if (data.ticket_status) {
        setTickets((current) => current.map((item) =>
          item.id === ticketId
            ? { ...item, status: data.ticket_status }
            : item
        ));
      }

      setSelfHealNotice(
        `${ticketId}: ${data.message || "Self-healing process completed."}`
      );
      await Promise.all([loadTickets(), loadAudit()]);
    } catch (error) {
      setSelfHealError(error.message || "Unable to complete self-healing.");
    } finally {
      setSelfHealLoadingId("");
    }
  }

  // ---------------- KNOWLEDGE / RAG ----------------

  async function searchKnowledge(event) {
    event.preventDefault();
    if (!knowledgeQuestion.trim() || knowledgeLoading) return;

    setKnowledgeLoading(true);
    setKnowledgeError("");
    setKnowledgeAnswer(null);

    try {
      const response = await fetch(`${API_URL}/api/knowledge/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: knowledgeQuestion.trim() }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(errorMessage(data, "Knowledge search failed."));
      }

      setKnowledgeAnswer(data);
    } catch (error) {
      setKnowledgeError(error.message || "Unable to search the knowledge base.");
    } finally {
      setKnowledgeLoading(false);
    }
  }

  // Declared BEFORE the effect that calls it. This fixes the white screen.
  const loadKnowledgeArticles = useCallback(async () => {
    setArticlesLoading(true);
    setArticlesError("");

    try {
      const response = await fetch(`${API_URL}/api/knowledge/articles`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          errorMessage(data, "Could not load knowledge articles.")
        );
      }

      const articles = Array.isArray(data)
        ? data
        : data?.articles || data?.knowledge || data?.items || [];

      setKnowledgeArticles(articles);
    } catch (error) {
      console.error("Knowledge catalogue error:", error);
      setArticlesError(
        error.message ||
        "Unable to load articles. Check the backend endpoint."
      );
    } finally {
      setArticlesLoading(false);
    }
  }, []);

  // ---------------- SOFTWARE REQUESTS ----------------

  const loadSoftwareData = useCallback(async () => {
    setSoftwareLoading(true);
    setSoftwareError("");

    try {
      const [catalogueResponse, requestsResponse] = await Promise.all([
        fetch(`${API_URL}/api/software/catalogue`),
        fetch(`${API_URL}/api/software/requests`),
      ]);

      const catalogueData = await catalogueResponse.json();
      const requestsData = await requestsResponse.json();

      if (!catalogueResponse.ok) {
        throw new Error(errorMessage(
          catalogueData, "Could not load software catalogue."
        ));
      }

      if (!requestsResponse.ok) {
        throw new Error(errorMessage(
          requestsData, "Could not load software requests."
        ));
      }

      const catPayload = catalogueData?.data || catalogueData;
      const reqPayload = requestsData?.data || requestsData;

      const catalogue = Array.isArray(catPayload)
        ? catPayload
        : catPayload.software || catPayload.catalogue ||
          catPayload.items || [];

      const requests = Array.isArray(reqPayload)
        ? reqPayload
        : reqPayload.requests || reqPayload.software_requests || [];

      setSoftwareCatalogue(catalogue);
      setSoftwareRequests(requests);

      setSelectedSoftware((current) =>
        current && catalogue.some((item) => softwareId(item) === current)
          ? current
          : catalogue.length ? softwareId(catalogue[0]) : ""
      );
    } catch (error) {
      console.error("Software loading error:", error);
      setSoftwareError(error.message || "Could not load software data.");
    } finally {
      setSoftwareLoading(false);
    }
  }, []);

  async function submitSoftwareRequest(event) {
    event.preventDefault();
    if (!selectedSoftware || !justification.trim() || softwareSubmitting) return;

    const item = softwareCatalogue.find(
      (entry) => softwareId(entry) === selectedSoftware
    );

    setSoftwareSubmitting(true);
    setSoftwareError("");
    setSoftwareNotice("");

    try {
      const response = await fetch(`${API_URL}/api/software/requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          software: selectedSoftware,
          software_name: softwareName(item),
          requested_by: requestedBy.trim() || "Employee",
          justification: justification.trim(),
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(errorMessage(data, "Software request failed."));
      }

      setSoftwareNotice(
        data.message || "Software request submitted successfully. Provisioning is simulated."
      );
      setJustification("");
      await Promise.all([loadSoftwareData(), loadAudit(), loadTickets()]);
    } catch (error) {
      setSoftwareError(error.message || "Unable to submit software request.");
    } finally {
      setSoftwareSubmitting(false);
    }
  }

  // ---------------- AUDIT ----------------

  const loadAudit = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/audit`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(errorMessage(data, "Could not load audit history."));
      }

      setAuditRecords(Array.isArray(data)
        ? data
        : data?.records || data?.audit_logs || data?.audit || []);
      setAuditError("");
    } catch (error) {
      console.error("Audit loading error:", error);
      setAuditError(error.message || "Could not load audit history.");
    }
  }, []);

  // Initial data load.
  useEffect(() => {
    loadTickets();
    loadSoftwareData();
    loadAudit();
  }, [loadTickets, loadSoftwareData, loadAudit]);

  // This effect is now AFTER loadKnowledgeArticles is declared.
  useEffect(() => {
    if (activePage === "knowledge") loadKnowledgeArticles();
  }, [activePage, loadKnowledgeArticles]);

  // ---------------- SHARED UI ----------------

  const openTickets = tickets.filter(
    (ticket) => !String(ticket.status).toLowerCase().includes("resolved")
  ).length;
  const resolvedTickets = tickets.length - openTickets;
  const escalatedTickets = tickets.filter(
    (ticket) => String(ticket.status).toLowerCase().includes("escalat")
  ).length;

  const pageTitles = {
    dashboard: "Dashboard",
    employee: "Employee Portal",
    analysis: "AI Analysis",
    knowledge: "Knowledge Base",
    software: "Software Requests",
  };

  function renderTicketForm() {
    return (
      <section className="panel">
        <h2>Create an IT support ticket</h2>
        <p>Describe your issue. Do not include passwords or secret credentials.</p>

        <form onSubmit={submitRequest}>
          <label htmlFor="ticket-description">Describe your issue</label>
          <textarea
            id="ticket-description"
            rows={4}
            value={request}
            onChange={(event) => setRequest(event.target.value)}
            placeholder="Example: My VPN is not connecting..."
            required
          />
          <button className="primary-button" disabled={ticketSubmitting}>
            {ticketSubmitting ? "Submitting..." : "Submit ticket"}
          </button>
        </form>

        {ticketError && <p className="form-error" role="alert">{ticketError}</p>}
        {ticketNotice && <p className="form-success" role="status">{ticketNotice}</p>}
      </section>
    );
  }

  function renderTicketTable(limit) {
    const rows = typeof limit === "number" ? tickets.slice(0, limit) : tickets;

    return (
      <>
        {ticketsLoading && <p>Loading tickets...</p>}
        {ticketError && <p className="form-error">{ticketError}</p>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Issue</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((ticket) => {
                const eligible = Boolean(getSelfHealAction(ticket));
                const busy = selfHealLoadingId === ticket.id;
                const resolved = String(ticket.status).toLowerCase().includes("resolved");

                return (
                  <tr key={ticket.id}>
                    <td>{ticket.id}</td>
                    <td>{ticket.title}</td>
                    <td>{ticket.category}</td>
                    <td>{ticket.priority}</td>
                    <td><span className="ticket-status">{ticket.status}</span></td>
                    <td>
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={!eligible || busy || resolved}
                        onClick={() => handleSelfHeal(ticket)}
                        title={!eligible ? "No supported mock action" : ""}
                      >
                        {busy ? "Working..." : resolved ? "Resolved" : "Self-heal"}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {!rows.length && !ticketsLoading && (
                <tr><td colSpan={6}>No tickets found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {selfHealError && <p className="form-error">{selfHealError}</p>}
        {selfHealNotice && <p className="form-success">{selfHealNotice}</p>}
      </>
    );
  }

  function renderKnowledgePanel() {
    return (
      <section className="panel">
        <h2>Ask HelpPilot AI</h2>
        <p>Answers are grounded in retrieved IT knowledge. Unsupported questions should be escalated.</p>

        <form onSubmit={searchKnowledge}>
          <label htmlFor="knowledge-question">Your IT question</label>
          <textarea
            id="knowledge-question"
            rows={3}
            value={knowledgeQuestion}
            onChange={(event) => setKnowledgeQuestion(event.target.value)}
            placeholder="Example: How do I troubleshoot VPN connectivity?"
            required
          />
          <button className="primary-button" disabled={knowledgeLoading}>
            {knowledgeLoading ? "Searching..." : "Ask AI"}
          </button>
        </form>

        {knowledgeError && <p className="form-error">{knowledgeError}</p>}

        {knowledgeAnswer && (
          <div className="knowledge-answer">
            <h3>AI response</h3>
            <p style={{ whiteSpace: "pre-wrap" }}>
              {knowledgeAnswer.answer ||
               knowledgeAnswer.response ||
               knowledgeAnswer.message ||
               "No answer was returned."}
            </p>

            {knowledgeAnswer.escalated && (
              <p className="form-error">
                Human support is recommended because the answer could not be confidently grounded.
              </p>
            )}

            {(knowledgeAnswer.sources || knowledgeAnswer.results || []).length > 0 && (
              <>
                <h4>Knowledge sources</h4>
                <ul>
                  {(knowledgeAnswer.sources || knowledgeAnswer.results).map((source, index) => (
                    <li key={source.document_id || source.id || index}>
                      {source.title || source.document_id || source.source || "Knowledge article"}
                      {source.distance != null
                        ? ` (distance: ${Number(source.distance).toFixed(3)})`
                        : ""}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </section>
    );
  }

  function renderKnowledgePage() {
    return (
      <>
        <section className="welcome">
          <div>
            <p className="eyebrow">KNOWLEDGE MANAGEMENT</p>
            <h2>IT Knowledge Library</h2>
            <p>Browse approved IT support articles and troubleshooting guidance.</p>
          </div>
          <span className="welcome-icon">▤</span>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Knowledge Articles</h2>
              <p>{knowledgeArticles.length} article(s) loaded</p>
            </div>
            <button
              type="button"
              className="secondary-button"
              onClick={loadKnowledgeArticles}
              disabled={articlesLoading}
            >
              {articlesLoading ? "Loading..." : "Refresh articles"}
            </button>
          </div>

          {articlesError && <p className="form-error">{articlesError}</p>}
          {articlesLoading && <p>Loading knowledge articles...</p>}

          <div className="knowledge-article-list">
            {knowledgeArticles.map((article, index) => (
              <details
                className="knowledge-article-card"
                key={article.document_id || article._id || article.title || index}
              >
                <summary>
                  <div className="knowledge-article-heading">
                    <span className="knowledge-article-id">
                      {article.document_id || "KB"}
                    </span>
                    <div>
                      <h3>{article.title || "Untitled article"}</h3>
                      <span className="knowledge-category">
                        {article.category || "General"}
                      </span>
                    </div>
                  </div>
                </summary>
                <div className="knowledge-article-content">
                  <p>{article.content || article.text || "Article content is not available."}</p>
                </div>
              </details>
            ))}
          </div>

          {!articlesLoading && !articlesError && knowledgeArticles.length === 0 && (
            <p>
              No articles were returned. If the backend does not provide
              <code> /api/knowledge/articles</code>, add that endpoint or use the AI Analysis
              page to query the indexed knowledge base.
            </p>
          )}
        </section>
      </>
    );
  }

  function renderSoftwarePage() {
    return (
      <>
        <section className="welcome">
          <div>
            <p className="eyebrow">SOFTWARE PROVISIONING</p>
            <h2>Request approved software</h2>
            <p>Requests create a record and simulate provisioning; nothing is installed on your computer.</p>
          </div>
          <span className="welcome-icon">▣</span>
        </section>

        <section className="panel">
          <h2>New software request</h2>
          {softwareError && <p className="form-error">{softwareError}</p>}
          {softwareNotice && <p className="form-success">{softwareNotice}</p>}

          <form onSubmit={submitSoftwareRequest}>
            <label htmlFor="requester">Requested by</label>
            <input
              id="requester"
              value={requestedBy}
              onChange={(event) => setRequestedBy(event.target.value)}
              required
            />

            <label htmlFor="software-select">Software catalogue</label>
            <select
              id="software-select"
              value={selectedSoftware}
              onChange={(event) => setSelectedSoftware(event.target.value)}
              required
            >
              {softwareCatalogue.map((item, index) => (
                <option key={softwareId(item) || index} value={softwareId(item)}>
                  {softwareName(item)}
                </option>
              ))}
            </select>

            {softwareLoading && <p>Loading software catalogue...</p>}
            {!softwareLoading && !softwareCatalogue.length && (
              <p>No catalogue items returned by the backend.</p>
            )}

            <label htmlFor="justification">Business justification</label>
            <textarea
              id="justification"
              rows={3}
              value={justification}
              onChange={(event) => setJustification(event.target.value)}
              placeholder="Explain why you need this software."
              required
            />

            <button
              className="primary-button"
              disabled={softwareSubmitting || !softwareCatalogue.length}
            >
              {softwareSubmitting ? "Submitting..." : "Submit software request"}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Previous requests</h2>
              <p>Mock provisioning status and linked ticket IDs</p>
            </div>
            <button
              type="button"
              className="secondary-button"
              onClick={loadSoftwareData}
            >
              Refresh
            </button>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Request</th>
                  <th>Software</th>
                  <th>Requested by</th>
                  <th>Status</th>
                  <th>Ticket</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {softwareRequests.map((item, index) => (
                  <tr key={item.id || item.request_id || item._id || index}>
                    <td>{item.id || item.request_id || "—"}</td>
                    <td>{typeof item.software === "object"
                      ? softwareName(item.software)
                      : item.software || item.software_name || "—"}</td>
                    <td>{item.requested_by || "—"}</td>
                    <td>{item.status || "Submitted"}</td>
                    <td>{item.ticket_id || "—"}</td>
                    <td>{formatDate(item.created_at)}</td>
                  </tr>
                ))}
                {!softwareRequests.length && (
                  <tr><td colSpan={6}>No software requests yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </>
    );
  }

  function renderDashboard() {
    return (
      <>
        <section className="welcome">
          <div>
            <p className="eyebrow">EMPLOYEE SUPPORT CENTER</p>
            <h2>How can we help you today?</h2>
            <p>Submit an IT issue or service request to get started.</p>
          </div>
          <span className="welcome-icon">✦</span>
        </section>

        <section className="stats">
          <div className="stat-card"><p>Total Tickets</p><h2>{tickets.length}</h2><span>All recorded tickets</span></div>
          <div className="stat-card"><p>Open Tickets</p><h2>{openTickets}</h2><span>Awaiting resolution</span></div>
          <div className="stat-card"><p>Resolved Tickets</p><h2>{resolvedTickets}</h2><span>Marked resolved</span></div>
          <div className="stat-card"><p>Escalated Tickets</p><h2>{escalatedTickets}</h2><span>Needs support attention</span></div>
        </section>

        <section className="content-grid">
          {renderTicketForm()}
          <div className="panel quick-panel">
            <h2>Quick actions</h2>
            <p>Common IT support requests</p>
            <button className="quick-action" onClick={() => {
              setRequest("My password has expired.");
              setActivePage("employee");
            }}>
              <span className="action-icon">🔐</span>
              <span><strong>Password reset</strong><small>Account access assistance</small></span>
              <span className="arrow">→</span>
            </button>
            <button className="quick-action" onClick={() => {
              setRequest("My VPN is not connecting.");
              setActivePage("employee");
            }}>
              <span className="action-icon">🌐</span>
              <span><strong>VPN connectivity</strong><small>Network troubleshooting</small></span>
              <span className="arrow">→</span>
            </button>
            <button className="quick-action" onClick={() => setActivePage("software")}>
              <span className="action-icon">💻</span>
              <span><strong>Software installation</strong><small>Request approved software</small></span>
              <span className="arrow">→</span>
            </button>
          </div>
        </section>

        <section className="panel tickets-panel">
          <div className="panel-heading">
            <div><h2>Recent tickets</h2><p>Your latest IT support requests</p></div>
            <button className="secondary-button" onClick={loadTickets} disabled={ticketsLoading}>
              {ticketsLoading ? "Refreshing..." : "Refresh tickets"}
            </button>
          </div>
          {renderTicketTable(6)}
        </section>
      </>
    );
  }

  function renderEmployeePage() {
    return (
      <>
        <section className="welcome">
          <div>
            <p className="eyebrow">EMPLOYEE SELF-SERVICE</p>
            <h2>Report an issue</h2>
            <p>Create a ticket for IT to review and resolve.</p>
          </div>
          <span className="welcome-icon">＋</span>
        </section>
        <section className="content-grid">
          {renderTicketForm()}
          <div className="panel">
            <h2>Before you submit</h2>
            <p>
              Describe what happened, any error messages, and what you were
              trying to do. Never include passwords or secret credentials.
            </p>
          </div>
        </section>
        <section className="panel tickets-panel">
          <div className="panel-heading">
            <div><h2>Recent tickets</h2><p>Tickets saved by the backend</p></div>
            <button className="secondary-button" onClick={loadTickets}>Refresh</button>
          </div>
          {renderTicketTable()}
        </section>
      </>
    );
  }

  function renderAnalysisPage() {
    return (
      <>
        <section className="welcome">
          <div>
            <p className="eyebrow">AI-ASSISTED SUPPORT</p>
            <h2>Knowledge-grounded analysis</h2>
            <p>Answers use retrieved knowledge, show sources and escalate when confidence is low.</p>
          </div>
          <span className="welcome-icon">✦</span>
        </section>

        {renderKnowledgePanel()}

        <section className="panel tickets-panel">
          <div className="panel-heading">
            <div>
              <h2>Ticket self-healing</h2>
              <p>Eligible account-access and VPN actions are simulated.</p>
            </div>
            <button className="secondary-button" onClick={() => {
              loadTickets();
              loadAudit();
            }}>Refresh data</button>
          </div>
          {renderTicketTable()}
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div><h2>Automation audit trail</h2><p>Recent simulated actions recorded by the backend.</p></div>
            <button className="secondary-button" onClick={loadAudit}>Refresh audit</button>
          </div>
          {auditError && <p className="form-error">{auditError}</p>}
          <div className="table-wrap">
            <table>
              <thead><tr><th>Ticket</th><th>Action</th><th>Status</th><th>Mode</th><th>Timestamp</th></tr></thead>
              <tbody>
                {auditRecords.slice(0, 10).map((record, index) => (
                  <tr key={record._id || `${record.ticket_id}-${index}`}>
                    <td>{record.ticket_id || "—"}</td>
                    <td>{record.action || "—"}</td>
                    <td>{record.status || "—"}</td>
                    <td>{record.execution_mode || "mock"}</td>
                    <td>{formatDate(record.created_at)}</td>
                  </tr>
                ))}
                {!auditRecords.length && <tr><td colSpan={5}>No audit records yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      </>
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h2 className="brand">HelpPilot AI</h2>
        <p className="brand-subtitle">INTELLIGENT IT SUPPORT</p>

        <nav aria-label="Main navigation">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${activePage === item.id ? "active" : ""}`}
              onClick={() => setActivePage(item.id)}
              aria-current={activePage === item.id ? "page" : undefined}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          Prototype environment
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">IT SERVICE MANAGEMENT</p>
            <h1>{pageTitles[activePage]}</h1>
          </div>
          <div className="user-badge">AN</div>
        </header>

        {activePage === "dashboard" && renderDashboard()}
        {activePage === "employee" && renderEmployeePage()}
        {activePage === "analysis" && renderAnalysisPage()}
        {activePage === "knowledge" && renderKnowledgePage()}
        {activePage === "software" && renderSoftwarePage()}

        <footer>
          HelpPilot AI · ITSM Hackathon Prototype · Mock integrations only
        </footer>
      </main>
    </div>
  );
}

export default App;
