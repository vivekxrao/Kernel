import React, { useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';

function FitBounds({ data }) {
  const map = useMap();
  useEffect(() => {
    if (!data?.features?.length) return;
    try {
      const bounds = L.geoJSON(data).getBounds();
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20], maxZoom: 16 });
    } catch (error) {
      console.warn('Could not fit building bounds:', error);
    }
  }, [data, map]);
  return null;
}

function styleFor(feature, threshold) {
  const raw = feature?.properties?.mean_t;
  const score = Number(raw);
  let color = '#8796a8';
  if (raw != null && Number.isFinite(score)) {
    color = score >= 4 ? '#ef535b' : score > threshold ? '#f0a53f' : '#31c987';
  }
  return { color, weight: 1, fillColor: color, fillOpacity: 0.58 };
}

export default function DamageMap({ data, onSelect, threshold = 3.3, height = '100%' }) {
  return (
    <MapContainer center={[48.59, 37.99]} zoom={13} scrollWheelZoom className="kd-leaflet-map" style={{ height, width: '100%' }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {data?.features?.length > 0 && <>
        <FitBounds data={data} />
        <GeoJSON
          key={`${data.features.length}-${threshold}`}
          data={data}
          style={(feature) => styleFor(feature, threshold)}
          onEachFeature={(feature, layer) => {
            const p = feature.properties || {};
            const id = p.building_id ?? p.id ?? '—';
            const score = p.mean_t == null ? 'N/A' : Number(p.mean_t).toFixed(2);
            layer.bindTooltip(`Building ${id} · Mean T: ${score}`);
            layer.on('click', () => onSelect?.({ ...p, geometry: feature.geometry }));
          }}
        />
      </>}
    </MapContainer>
  );
}
