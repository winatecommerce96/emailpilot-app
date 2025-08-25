import React from "react";

export function HealthBadge({ label = "OK" }) {
  return (
    <div style={{
      display:"inline-flex",
      alignItems:"center",
      gap:8,
      padding:"6px 10px",
      border:"1px solid #d1d5db",
      borderRadius:999,
      fontSize:12
    }}>
      <span style={{
        width:8,
        height:8,
        borderRadius:"50%",
        background:"#10b981",
        display:"inline-block"
      }} />
      <span>{label}</span>
    </div>
  );
}

export default function HealthCheck() {
  return (
    <div style={{
      marginTop:12,
      padding:"12px 14px",
      border:"1px dashed #d1d5db",
      borderRadius:12,
      background:"#fafafa"
    }}>
      <div style={{fontWeight:600, marginBottom:6}}>Import/Export Sanity</div>
      <div style={{fontSize:14}}>
        • Default export rendered (this box).<br/>
        • Named export rendered (green badge above).
      </div>
    </div>
  );
}